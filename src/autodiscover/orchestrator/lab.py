"""Complete persisted minimum research loop. Proposals never decide their own success."""

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments import evaluator, runner
from autodiscover.experiments.contracts import Plan
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal, generate
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.contracts import RunStatus, Stage
from autodiscover.orchestrator.durability import atomic_json
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, BudgetError


class Lab:
    def __init__(self, root: Path):
        self.store = Store(root)
        self.artifacts = Artifacts(root / "artifacts")

    def demo(
        self,
        topic: str = "consumer, gaming and telemetry data",
        *,
        limits: Limits | None = None,
        stop_after: int | None = None,
        algorithm: str = "rle",
    ) -> str:
        run_id = self.store.create_run(topic, (limits or Limits()).model_dump(mode="json"))
        self.resume(run_id, stop_after=stop_after, demo_algorithm=algorithm)
        return run_id

    def latest(self, run_id: str, stage: Stage) -> dict[str, Any]:
        outputs = [s for s in self.store.outputs(run_id) if s["stage"] == stage]
        if not outputs:
            raise ValueError("Required predecessor result missing")
        return json.loads(outputs[-1]["output_json"])

    def hypothesis(self, run_id: str) -> Hypothesis:
        digest = self.latest(run_id, Stage.HYPOTHESIZE)["hypothesis_ids"][0]
        return Hypothesis.model_validate(self.artifacts.get_json(digest))

    def plan(self, run_id: str) -> Plan:
        digest = self.latest(run_id, Stage.DESIGN)["plan_digest"]
        plan = Plan.model_validate(self.artifacts.get_json(digest))
        if plan.digest != digest:
            raise ValueError("Preregistered plan integrity mismatch")
        return plan

    def resume(
        self,
        run_id: str,
        *,
        stop_after: int | None = None,
        demo_algorithm: str = "rle",
        router: Router | None = None,
    ) -> None:
        verify_chain(self.store)
        row = self.store.get_run(run_id)
        if row["status"] == RunStatus.COMPLETED:
            self.report(run_id)
            return
        limits = Limits.model_validate_json(row["policy_json"])
        owner = "lab-" + str(uuid4())
        fence = self.store.claim(run_id, owner, seconds=180)
        count = 0
        try:
            while self.store.get_run(run_id)["status"] == RunStatus.ACTIVE:
                row = self.store.get_run(run_id)
                stage, version = Stage(row["stage"]), row["version"]
                # Bound development/demo operation even before the full branch director exists.
                if version >= 12 * limits.max_hypotheses_per_cycle:
                    self.store.control(run_id, "pause")
                    break
                self.store.heartbeat(run_id, owner, fence, seconds=180)
                started = time.monotonic()
                before_usage = Budget(self.store).totals(run_id)
                output, target, reason = self._stage(
                    run_id, stage, version, limits, router=router, demo_algorithm=demo_algorithm
                )
                self.store.complete_step(
                    run_id,
                    owner=owner,
                    fence=fence,
                    expected=stage,
                    version=version,
                    key=f"{stage}:{version}",
                    output=output,
                    target=target,
                    reason=reason,
                    resources={
                        "elapsed_seconds": time.monotonic() - started,
                        "cost_usd": str(
                            Decimal(Budget(self.store).totals(run_id)["charged_usd"])
                            - Decimal(before_usage["charged_usd"])
                        ),
                    },
                )
                count += 1
                if stop_after is not None and count >= stop_after:
                    break
        except BudgetError:
            if self.store.get_run(run_id)["status"] == RunStatus.ACTIVE:
                self.store.control(run_id, "pause")
            self.report(run_id)
        except (runner.ExecutionError, evaluator.EvaluationError) as error:
            self.store.fail_step(run_id, owner, fence, str(error))
            raise
        finally:
            self.store.release(run_id, owner, fence)
        self.report(run_id)

    def _stage(
        self,
        run_id: str,
        stage: Stage,
        version: int,
        limits: Limits,
        *,
        router: Router | None,
        demo_algorithm: str,
    ) -> tuple[dict[str, Any], Stage | None, str | None]:
        topic = self.store.get_run(run_id)["topic"]
        output: dict[str, Any]
        if stage == Stage.DISCOVER:
            output = {
                "questions": [f"Can lossless encoding improve repeated data storage in {topic}?"]
            }
        elif stage == Stage.RESEARCH:
            output = {
                "source_ids": [],
                "coverage_limitations": "Offline deterministic demo; "
                "prior art is not retrieved. Novelty remains unknown.",
            }
        elif stage == Stage.HYPOTHESIZE:
            router = router or Router(
                self.store,
                {"HYPOTHESIZE": [MockProvider([demo_proposal(topic, algorithm=demo_algorithm)])]},
            )
            h = generate(router, run_id, topic, key=f"hypothesis:{version}")
            digest = self.artifacts.put_json(h.model_dump(mode="json"))
            output = {"hypothesis_ids": [digest]}
        elif stage == Stage.PRIORITIZE:
            output = {"selected_ids": [self.hypothesis(run_id).identity]}
        elif stage == Stage.DESIGN:
            h = self.hypothesis(run_id)
            plan = Plan(
                hypothesis_id=h.identity,
                algorithm=h.algorithm,
                minimum_savings=h.threshold,
                data_profile=h.data_profile,
                seconds=min(10, limits.max_experiment_seconds),
            )
            digest = self.artifacts.put_json(plan.model_dump(mode="json"))
            output = {"plan_id": h.identity, "plan_digest": digest}
        elif stage == Stage.PREFLIGHT:
            result = runner.preflight(self.plan(run_id), limits)
            output = {k: result[k] for k in ("plan_id", "plan_digest", "authorized")}
        elif stage == Stage.EXECUTE:
            plan = self.plan(run_id)
            raw = runner.run(plan, limits)
            digest = self.artifacts.put_json(raw)
            output = {
                "artifact_digest": digest,
                "plan_digest": plan.digest,
                "elapsed_seconds": raw["elapsed_seconds"],
            }
        elif stage == Stage.VERIFY:
            plan = self.plan(run_id)
            raw = self.artifacts.get_json(self.latest(run_id, Stage.EXECUTE)["artifact_digest"])
            report = evaluator.evaluate(plan, raw)
            digest = self.artifacts.put_json(report)
            output = {"passed": report["passed"], "report_digest": digest}
            if not report["passed"]:
                return output, Stage.HYPOTHESIZE, "Held-out threshold failed; revision required"
        elif stage == Stage.REPLICATE:
            plan = self.plan(run_id)
            results = []
            passed = True
            for index in range(1, plan.replications + 1):
                raw = runner.run(plan, limits, replication=index)
                raw_digest = self.artifacts.put_json(raw)
                report = evaluator.evaluate(plan, raw, replication=index)
                report["raw_artifact_digest"] = raw_digest
                results.append(self.artifacts.put_json(report))
                passed = passed and report["passed"]
            output = {"passed": passed, "report_digests": results}
            if not passed:
                return output, Stage.HYPOTHESIZE, "Replication threshold failed; revision required"
        elif stage == Stage.ASSESS:
            verified = self.latest(run_id, Stage.VERIFY)["passed"]
            replicated = self.latest(run_id, Stage.REPLICATE)["passed"]
            output = {
                "technical_success": verified and replicated,
                "novelty": "unknown",
                "limitations": (
                    "Synthetic fixture benchmark of known encoding; no novelty assessment"
                ),
            }
        elif stage == Stage.VALIDATE_MARKET:
            output = {"level": 0, "evidence_ids": [], "validated": False}
        else:
            output = {
                "decision": "stop",
                "rationale": "Bounded demonstration complete; "
                "no novelty/commercial claim or further spending authorized",
            }
        return output, None, None

    def report(self, run_id: str) -> dict[str, Any]:
        row = self.store.get_run(run_id)
        assessment = None
        market = None
        for step in self.store.outputs(run_id):
            if step["stage"] == Stage.ASSESS:
                assessment = json.loads(step["output_json"])
            if step["stage"] == Stage.VALIDATE_MARKET:
                market = json.loads(step["output_json"])
        report = {
            "schema_version": 1,
            "run_id": run_id,
            "status": row["status"],
            "stage": row["stage"],
            "completed_steps": len(self.store.outputs(run_id)),
            "assessment": assessment,
            "commercial": market,
            "usage": Budget(self.store).totals(run_id),
            "evidence": verify_chain(self.store),
            "mode": "offline trusted encoding demo; sources/live providers unverified",
        }
        atomic_json(self.store.root / "reports" / f"{run_id}.json", report)
        return report
