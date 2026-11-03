"""Complete persisted minimum research loop. Proposals never decide their own success."""

import json
import time
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from autodiscover.commercial.contracts import Opportunity
from autodiscover.commercial.service import Market
from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts
from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments import evaluator, runner
from autodiscover.experiments.allocation_contracts import AllocationPlan
from autodiscover.experiments.allocation_evaluator import AllocationEvaluationError
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.registry import RegisteredPlan, evaluate_registered, parse_plan
from autodiscover.hypotheses.allocation import AllocationHypothesis
from autodiscover.hypotheses.director import Director, DuplicateHypothesis, SearchStopped
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal, generate
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.models.contracts import ProviderError
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.contracts import RunStatus, Stage
from autodiscover.orchestrator.durability import atomic_json
from autodiscover.orchestrator.jobs import Jobs, ResourceBusy
from autodiscover.orchestrator.loops import ProgressGuard
from autodiscover.orchestrator.store import StateError, Store
from autodiscover.research.catalog import Catalog
from autodiscover.research.intelligence import retrieve_publications, synthesize
from autodiscover.research.retrieval import Fetcher
from autodiscover.security.budget import Budget, BudgetError
from autodiscover.security.cancellation import cancellation_scope
from autodiscover.security.processes import local_owner


class Lab:
    def __init__(self, root: Path):
        self.store = Store(root)
        self.artifacts = Artifacts(root / "artifacts")
        self.director = Director(self.store)
        self.jobs = Jobs(self.store)

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

    def explore(
        self,
        topic: str,
        candidates: Sequence[Hypothesis | AllocationHypothesis | ResearchProposal],
        *,
        limits: Limits | None = None,
    ) -> str:
        policy = (limits or Limits()).model_copy(update={"explore_existing_candidates": True})
        run_id = self.store.create_run(topic, policy.model_dump(mode="json"))
        self.director.configure(run_id)
        for candidate in candidates:
            self.director.register(run_id, candidate)
        self.resume(run_id)
        return run_id

    def latest(self, run_id: str, stage: Stage) -> dict[str, Any]:
        outputs = [s for s in self.store.outputs(run_id) if s["stage"] == stage]
        if not outputs:
            raise ValueError("Required predecessor result missing")
        return json.loads(outputs[-1]["output_json"])

    def hypothesis(self, run_id: str) -> Hypothesis:
        digest = self.latest(run_id, Stage.HYPOTHESIZE)["hypothesis_ids"][0]
        return Hypothesis.model_validate(self.artifacts.get_json(digest))

    def selected_hypothesis(
        self, run_id: str
    ) -> tuple[str, Hypothesis | AllocationHypothesis]:
        identifier = self.latest(run_id, Stage.PRIORITIZE)["selected_ids"][0]
        try:
            hypothesis = self.director.get(run_id, identifier)
        except ValueError:
            # Pre-phase-6 PRIORITIZE stored semantic identity, not the artifact address.
            # Adopt it explicitly without editing historical evidence or replaying execution.
            hypothesis = self.hypothesis(run_id)
            if hypothesis.identity != identifier:
                raise ValueError("Historical selection does not match hypothesis") from None
            registered = self.director.register(run_id, hypothesis)
            adopted = self.director.select(run_id, key="legacy-prioritize:" + registered)
            if adopted != registered:
                raise SearchStopped("LEGACY_SELECTION_REQUIRES_REVIEW") from None
            identifier = registered
        if not isinstance(hypothesis, (Hypothesis, AllocationHypothesis)):
            raise SearchStopped("NO_REVIEWED_EXECUTION_ADAPTER")
        return identifier, hypothesis

    def plan(self, run_id: str) -> RegisteredPlan:
        digest = self.latest(run_id, Stage.DESIGN)["plan_digest"]
        plan = parse_plan(self.artifacts.get_json(digest))
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
        stop_requested: Callable[[], bool] | None = None,
    ) -> None:
        verify_chain(self.store)
        row = self.store.get_run(run_id)
        if row["status"] == RunStatus.COMPLETED:
            self.report(run_id)
            return
        limits = Limits.model_validate_json(row["policy_json"])
        owner = local_owner()
        fence = self.store.claim(run_id, owner, seconds=180)
        count = 0
        try:
            while self.store.get_run(run_id)["status"] == RunStatus.ACTIVE:
                if stop_requested and stop_requested():
                    break
                row = self.store.get_run(run_id)
                stage, version = Stage(row["stage"]), row["version"]
                # Bound development/demo operation even before the full branch director exists.
                if version >= 12 * limits.max_hypotheses_per_cycle:
                    self.director.stop(run_id, "STAGE_TRANSITION_LIMIT")
                    self.store.control(run_id, "pause")
                    break
                self.store.heartbeat(run_id, owner, fence, seconds=180)
                started = time.monotonic()
                before_usage = Budget(self.store).totals(run_id)

                def interrupted(stage_version: int = version) -> bool:
                    if stop_requested and stop_requested():
                        return True
                    try:
                        current = self.store.get_run(run_id)
                        if (
                            current["status"] != "ACTIVE"
                            or current["owner"] != owner
                            or current["fence"] != fence
                            or current["version"] != stage_version
                        ):
                            return True
                        if current["lease_until"] < self.store.clock() + 60:
                            self.store.heartbeat(run_id, owner, fence, seconds=180)
                    except StateError:
                        return True
                    return False

                with cancellation_scope(interrupted):
                    output, target, reason = self._stage(
                        run_id,
                        stage,
                        version,
                        limits,
                        router=router,
                        demo_algorithm=demo_algorithm,
                        owner=owner,
                        fence=fence,
                        stop_requested=stop_requested,
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
        except (runner.WorkInterrupted, ResourceBusy):
            # Control events/job evidence explain interruption; no scientific failure is fabricated.
            pass
        except (SearchStopped, DuplicateHypothesis) as error:
            self.director.stop(run_id, str(error))
            if self.store.get_run(run_id)["status"] == RunStatus.ACTIVE:
                self.store.control(run_id, "pause")
        except BudgetError as error:
            reason = str(error)
            self.director.stop(
                run_id,
                reason
                if reason.isupper() and " " not in reason
                else "INFERENCE_RECONCILIATION_REQUIRED",
            )
            if self.store.get_run(run_id)["status"] == RunStatus.ACTIVE:
                self.store.control(run_id, "pause")
            self.report(run_id)
        except ProviderError as error:
            if error.code == "PROVIDER_CANCEL_REQUESTED":
                self.director.stop(run_id, "INFERENCE_RECONCILIATION_REQUIRED")
                if self.store.get_run(run_id)["status"] == "ACTIVE":
                    self.store.control(run_id, "pause")
            else:
                current = self.store.get_run(run_id)
                if (
                    current["status"] == "ACTIVE"
                    and current["owner"] == owner
                    and current["fence"] == fence
                ):
                    self.store.fail_step(run_id, owner, fence, error.code)
                raise
        except (
            runner.ExecutionError,
            evaluator.EvaluationError,
            AllocationEvaluationError,
        ) as error:
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
        owner: str,
        fence: int,
        stop_requested: Callable[[], bool] | None = None,
    ) -> tuple[dict[str, Any], Stage | None, str | None]:
        topic = self.store.get_run(run_id)["topic"]
        output: dict[str, Any]
        if stage == Stage.DISCOVER:
            output = {
                "questions": [
                    f"Which reviewed experiment can measurably improve results in {topic}?"
                ]
            }
        elif stage == Stage.RESEARCH:
            if limits.allow_retrieval:
                catalog = Catalog(self.store)
                ids = catalog.sources(run_id)
                if not ids:
                    ids = retrieve_publications(
                        catalog, run_id, Fetcher(authorized=True), topic[:300]
                    )
                synthesis = synthesize(catalog, ids, topic)
                self.artifacts.put_json(synthesis)
                output = {"source_ids": ids, "coverage_limitations": synthesis["limitations"]}
            else:
                output = {
                    "source_ids": [],
                    "coverage_limitations": "Offline deterministic demo; "
                    "prior art is not retrieved. Novelty remains unknown.",
                }
        elif stage == Stage.HYPOTHESIZE:
            source_ids = self.latest(run_id, Stage.RESEARCH)["source_ids"]
            context = (
                Catalog(self.store).context(run_id)
                if source_ids
                else "Offline; no external sources"
            )
            verifications = [
                json.loads(step["output_json"])
                for step in self.store.outputs(run_id)
                if step["stage"] == Stage.VERIFY
            ]
            prior_failed = bool(verifications and not verifications[-1]["passed"])
            if router is None and prior_failed:
                parent_id, _parent = self.selected_hypothesis(run_id)
                try:
                    identifier = self.director.revise(
                        run_id, parent_id, verifications[-1]["report_digest"]
                    )
                except (SearchStopped, DuplicateHypothesis):
                    if limits.explore_existing_candidates and self.director.has_work(run_id):
                        return (
                            {
                                "hypothesis_ids": [
                                    n["id"] for n in self.director.tree(run_id)["nodes"]
                                ]
                            },
                            None,
                            None,
                        )
                    raise
                h = self.director.get(run_id, identifier)
            elif (
                router is None
                and limits.explore_existing_candidates
                and self.director.has_work(run_id)
            ):
                return (
                    {"hypothesis_ids": [n["id"] for n in self.director.tree(run_id)["nodes"]]},
                    None,
                    None,
                )
            else:
                if router is None:
                    proposal = demo_proposal(topic, algorithm=demo_algorithm)
                    proposal["source_ids"] = source_ids
                    router = Router(self.store, {"HYPOTHESIZE": [MockProvider([proposal])]})
                h = generate(
                    router, run_id, topic, key=f"hypothesis:{version}", source_context=context
                )
                if not set(h.source_ids).issubset(set(source_ids)):
                    raise ValueError("Hypothesis cites unavailable sources")
                identifier = self.director.register(run_id, h)
            stopped = ProgressGuard(self.store).observe(
                run_id,
                "hypothesis-generation",
                state=stage,
                signature=h.identity,
                observation_key=f"hypothesis:{version}",
                progress=float(len(self.director.tree(run_id)["nodes"])),
            )
            if stopped:
                raise SearchStopped(stopped)
            output = {"hypothesis_ids": [identifier]}
        elif stage == Stage.PRIORITIZE:
            identifier = self.director.select(run_id, key=f"prioritize:{version}")
            output = {"selected_ids": [identifier]}
        elif stage == Stage.DESIGN:
            _identifier, h = self.selected_hypothesis(run_id)
            seed = 42 + 9973 * (self.director.tree(run_id)["allocations"][-1]["ordinal"] - 1)
            if isinstance(h, AllocationHypothesis):
                plan: RegisteredPlan = AllocationPlan(
                    hypothesis_id=h.identity,
                    algorithm=h.algorithm,
                    minimum_gain=h.threshold,
                    data_profile=h.data_profile,
                    seconds=min(10, limits.max_experiment_seconds),
                    seed=seed,
                )
            else:
                plan = Plan(
                    hypothesis_id=h.identity,
                    algorithm=h.algorithm,
                    minimum_savings=h.threshold,
                    data_profile=h.data_profile,
                    seconds=min(10, limits.max_experiment_seconds),
                    seed=seed,
                )
            digest = self.artifacts.put_json(plan.model_dump(mode="json"))
            output = {"plan_id": h.identity, "plan_digest": digest}
        elif stage == Stage.PREFLIGHT:
            result = runner.preflight(self.plan(run_id), limits)
            output = {k: result[k] for k in ("plan_id", "plan_digest", "authorized")}
        elif stage == Stage.EXECUTE:
            plan = self.plan(run_id)
            raw = self.jobs.execute(
                run_id,
                owner=owner,
                run_fence=fence,
                stage_version=version,
                plan=plan,
                limits=limits,
                stop_requested=stop_requested,
            )
            digest = self.artifacts.put_json(raw)
            output = {
                "artifact_digest": digest,
                "plan_digest": plan.digest,
                "elapsed_seconds": raw["elapsed_seconds"],
            }
        elif stage == Stage.VERIFY:
            plan = self.plan(run_id)
            raw = self.artifacts.get_json(self.latest(run_id, Stage.EXECUTE)["artifact_digest"])
            report = evaluate_registered(plan, raw)
            report["raw_artifact_digest"] = self.latest(run_id, Stage.EXECUTE)["artifact_digest"]
            digest = self.artifacts.put_json(report)
            selected_id, _h = self.selected_hypothesis(run_id)
            self.director.record(run_id, selected_id, digest)
            output = {"passed": report["passed"], "report_digest": digest}
            if not report["passed"]:
                if (
                    limits.explore_existing_candidates
                    and (
                        isinstance(_h, AllocationHypothesis) or _h.algorithm != "identity"
                    )
                    and not self.director.has_work(run_id)
                ):
                    return (
                        output,
                        Stage.DECIDE,
                        "Failed independent test; bounded search has no eligible work",
                    )
                return output, Stage.HYPOTHESIZE, "Held-out threshold failed; revision required"
        elif stage == Stage.REPLICATE:
            plan = self.plan(run_id)
            results = []
            passed = True
            for index in range(1, plan.replications + 1):
                raw = self.jobs.execute(
                    run_id,
                    owner=owner,
                    run_fence=fence,
                    stage_version=version,
                    plan=plan,
                    limits=limits,
                    replication=index,
                    stop_requested=stop_requested,
                )
                raw_digest = self.artifacts.put_json(raw)
                report = evaluate_registered(plan, raw, replication=index)
                report["raw_artifact_digest"] = raw_digest
                report_digest = self.artifacts.put_json(report)
                results.append(report_digest)
                selected_id, _h = self.selected_hypothesis(run_id)
                self.director.record(run_id, selected_id, report_digest)
                passed = passed and report["passed"]
            output = {"passed": passed, "report_digests": results}
            if not passed:
                if limits.explore_existing_candidates and not self.director.has_work(run_id):
                    return (
                        output,
                        Stage.DECIDE,
                        "Replication failed; bounded search has no eligible work",
                    )
                return output, Stage.HYPOTHESIZE, "Replication threshold failed; revision required"
        elif stage == Stage.ASSESS:
            verified = self.latest(run_id, Stage.VERIFY)["passed"]
            replicated = self.latest(run_id, Stage.REPLICATE)["passed"]
            output = {
                "hypothesis_id": self.selected_hypothesis(run_id)[0],
                "technical_success": verified and replicated,
                "novelty": "unknown",
                "limitations": (
                    "Seeded synthetic reviewed experiment; known methods, no novelty "
                    "or commercial assessment"
                ),
            }
        elif stage == Stage.VALIDATE_MARKET:
            candidate_id, hypothesis = self.selected_hypothesis(run_id)
            market = Market(self.store)
            opportunity_id = market.current(run_id, candidate_id)
            if opportunity_id is None:
                opportunity_id = market.save(
                    run_id,
                    Opportunity(
                        candidate_id=candidate_id,
                        problem=hypothesis.question,
                        assumptions=["Potential application; no buyer evidence supplied"],
                    ),
                )
            assessment = market.assess(opportunity_id)
            output = {
                "level": assessment["level"],
                "evidence_ids": assessment["evidence_ids"],
                "validated": assessment["validated"],
                "opportunity_id": opportunity_id,
                "assessment_digest": self.artifacts.put_json(assessment),
            }
        else:
            if limits.explore_existing_candidates and self.director.has_work(run_id):
                return (
                    {"decision": "explore", "rationale": "Remaining bounded candidate allocation"},
                    Stage.HYPOTHESIZE,
                    "Explore eligible candidates without resetting branch limits",
                )
            output = {
                "decision": "stop",
                "rationale": "Bounded demonstration complete; "
                "no novelty/commercial claim or further spending authorized",
            }
        return output, None, None

    def report(self, run_id: str, *, persist: bool = True) -> dict[str, Any]:
        from autodiscover.orchestrator.store import SnapshotStore
        from autodiscover.reporting.reports import build_report

        with SnapshotStore(self.store.root) as snapshot:
            report = build_report(snapshot, run_id)
        if persist:
            atomic_json(self.store.root / "reports" / f"{run_id}.json", report)
        return report
