"""Persistent bounded branch allocation. Model scores never stand in for experiment evidence."""

import json
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.hypotheses.allocation import AllocationHypothesis
from autodiscover.hypotheses.engine import Hypothesis
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store


class SearchStopped(RuntimeError):
    pass


class DuplicateHypothesis(ValueError):
    def __init__(self, existing_id: str):
        super().__init__("DUPLICATE_HYPOTHESIS")
        self.existing_id = existing_id


class SearchPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_candidates: int = Field(default=5, ge=1, le=100)
    max_experiments: int = Field(default=5, ge=1, le=100)
    max_branch_experiments: int = Field(default=2, ge=1, le=100)
    exploration_fraction: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    max_depth: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def preserve_branch_diversification(self) -> "SearchPolicy":
        if self.max_branch_experiments > max(1, self.max_experiments // 2):
            raise ValueError("A root branch cannot consume the whole experiment allocation")
        return self


class Director:
    def __init__(self, store: Store):
        self.store = store
        self.artifacts = Artifacts(store.root / "artifacts", read_only=store.read_only)

    def configure(self, run_id: str, policy: SearchPolicy | None = None) -> SearchPolicy:
        limits = Limits.model_validate_json(self.store.get_run(run_id)["policy_json"])
        policy = policy or SearchPolicy(
            max_candidates=limits.max_hypotheses_per_cycle,
            max_experiments=limits.max_hypotheses_per_cycle,
            max_branch_experiments=max(1, limits.max_hypotheses_per_cycle // 2),
        )
        if (
            policy.max_candidates > limits.max_hypotheses_per_cycle
            or policy.max_experiments > limits.max_hypotheses_per_cycle
        ):
            raise ValueError("Director exceeds authorized run search limit")
        with self.store.connection(write=True) as db:
            existing = db.execute(
                "SELECT policy_json FROM director_state WHERE run_id=?", (run_id,)
            ).fetchone()
            encoded = canonical(policy.model_dump(mode="json"))
            if existing and existing[0] != encoded:
                raise ValueError("Persistent search policy cannot change during a run")
            if not existing:
                db.execute("INSERT INTO director_state VALUES(?,?,NULL)", (run_id, encoded))
                self.store._event(db, run_id, "search_configured", {"policy": policy.model_dump()})
        return policy

    def policy(self, run_id: str) -> SearchPolicy:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT policy_json FROM director_state WHERE run_id=?", (run_id,)
            ).fetchone()
        return SearchPolicy.model_validate_json(row[0]) if row else self.configure(run_id)

    def register(
        self,
        run_id: str,
        hypothesis: Hypothesis | AllocationHypothesis | ResearchProposal,
        *,
        evidence_id: str | None = None,
    ) -> str:
        policy = self.policy(run_id)
        if hypothesis.source_ids:
            from autodiscover.research.catalog import Catalog

            catalog = Catalog(self.store)
            for source_id in hypothesis.source_ids:
                catalog.source(source_id)
        digest = self.artifacts.put_json(hypothesis.model_dump(mode="json"))
        kind = (
            "encoding" if isinstance(hypothesis, Hypothesis)
            else "allocation" if isinstance(hypothesis, AllocationHypothesis)
            else "theoretical"
        )
        with self.store.connection(write=True) as db:
            existing = db.execute(
                "SELECT id FROM hypotheses WHERE run_id=? AND identity=?",
                (run_id, hypothesis.identity),
            ).fetchone()
            if existing:
                if existing[0] == digest:
                    return digest  # Same persisted content after interrupted registration.
                raise DuplicateHypothesis(existing[0])
            if (
                db.execute("SELECT COUNT(*) FROM hypotheses WHERE run_id=?", (run_id,)).fetchone()[
                    0
                ]
                >= policy.max_candidates
            ):
                raise SearchStopped("CANDIDATE_LIMIT")
            depth = 0
            if hypothesis.parent_id:
                parent = db.execute(
                    "SELECT * FROM hypotheses WHERE id=? AND run_id=?",
                    (hypothesis.parent_id, run_id),
                ).fetchone()
                if parent is None:
                    raise ValueError("Parent hypothesis must exist in the same run")
                if parent["kind"] == "encoding" and isinstance(hypothesis, Hypothesis):
                    original = Hypothesis.model_validate(self.artifacts.get_json(parent["id"]))
                    if (
                        hypothesis.threshold < original.threshold
                        or hypothesis.data_profile != original.data_profile
                        or hypothesis.comparator != original.comparator
                        or hypothesis.metric != original.metric
                    ):
                        raise ValueError("Revision cannot weaken criteria or change evaluated data")
                depth = parent["depth"] + 1
                if depth > policy.max_depth:
                    raise SearchStopped("BRANCH_DEPTH_LIMIT")
                if not evidence_id:
                    raise ValueError("Revision requires an actual evaluation artifact")
                evaluation = self.artifacts.get_json(evidence_id)
                if (
                    parent["kind"] != "encoding"
                    or evaluation.get("passed") is not False
                    or evaluation.get("plan_digest") is None
                ):
                    raise ValueError("Revision requires recorded failed experiment evidence")
                recorded = db.execute(
                    "SELECT 1 FROM branch_results WHERE run_id=? AND hypothesis_id=? "
                    "AND report_digest=? AND passed=0",
                    (run_id, hypothesis.parent_id, evidence_id),
                ).fetchone()
                if recorded is None:
                    raise ValueError("Evidence does not belong to the parent experiment")
            db.execute(
                "INSERT INTO hypotheses VALUES(?,?,?,?,?,?,?,?,?,NULL)",
                (
                    digest,
                    run_id,
                    hypothesis.identity,
                    hypothesis.parent_id,
                    depth,
                    hypothesis.domain,
                    kind,
                    "THEORETICAL" if kind == "theoretical" else "PENDING",
                    evidence_id,
                ),
            )
            self.store._event(
                db,
                run_id,
                "hypothesis_registered",
                {
                    "hypothesis_id": digest,
                    "identity": hypothesis.identity,
                    "parent_id": hypothesis.parent_id,
                    "depth": depth,
                    "domain": hypothesis.domain,
                    "kind": kind,
                    "revision_evidence": evidence_id,
                },
            )
        return digest

    def get(
        self, run_id: str, identifier: str
    ) -> Hypothesis | AllocationHypothesis | ResearchProposal:
        with self.store.connection() as db:
            row = db.execute(
                "SELECT kind FROM hypotheses WHERE id=? AND run_id=?", (identifier, run_id)
            ).fetchone()
        if row is None:
            raise ValueError("Unknown hypothesis in run")
        data = self.artifacts.get_json(identifier)
        schema = {
            "encoding": Hypothesis,
            "allocation": AllocationHypothesis,
            "theoretical": ResearchProposal,
        }.get(row[0])
        if schema is None:
            raise IntegrityError("Unknown executable hypothesis family")
        return schema.model_validate(data)

    def select(self, run_id: str, *, key: str) -> str:
        policy = self.policy(run_id)
        if not key or len(key) > 200:
            raise ValueError("Bounded stable allocation key required")
        with self.store.connection(write=True) as db:
            previous = db.execute(
                "SELECT hypothesis_id FROM branch_allocations WHERE run_id=? AND step_key=?",
                (run_id, key),
            ).fetchone()
            if previous:
                return previous[0]
            state = db.execute(
                "SELECT stopped_reason FROM director_state WHERE run_id=?", (run_id,)
            ).fetchone()
            if state[0]:
                raise SearchStopped(state[0])
            allocations = [
                dict(r)
                for r in db.execute("SELECT * FROM branch_allocations WHERE run_id=?", (run_id,))
            ]
            if len(allocations) >= policy.max_experiments:
                raise SearchStopped("EXPERIMENT_LIMIT")
            candidates = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM hypotheses WHERE run_id=? "
                    "AND kind IN ('encoding','allocation') "
                    "AND status IN ('PENDING','PROMISING') ORDER BY id",
                    (run_id,),
                )
            ]
            # The root branch shares credit with all its descendants, preventing mutation bypass.
            all_nodes = {
                r["id"]: dict(r)
                for r in db.execute("SELECT * FROM hypotheses WHERE run_id=?", (run_id,))
            }

            def root(identifier: str) -> str:
                while all_nodes[identifier]["parent_id"]:
                    identifier = all_nodes[identifier]["parent_id"]
                return identifier

            root_counts: dict[str, int] = {}
            domain_counts: dict[str, int] = {}
            family_counts: dict[str, int] = {}
            for allocation in allocations:
                branch = root(allocation["hypothesis_id"])
                root_counts[branch] = root_counts.get(branch, 0) + 1
                domain = all_nodes[allocation["hypothesis_id"]]["domain"]
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                kind = all_nodes[allocation["hypothesis_id"]]["kind"]
                family_counts[kind] = family_counts.get(kind, 0) + 1
            candidates = [
                c
                for c in candidates
                if root_counts.get(root(c["id"]), 0) < policy.max_branch_experiments
            ]
            if not candidates:
                raise SearchStopped("NO_ELIGIBLE_BRANCH")
            explored = sum(a["mode"] == "explore" for a in allocations)
            explore = explored < math.ceil((len(allocations) + 1) * policy.exploration_fraction)
            if explore:
                candidates.sort(
                    key=lambda c: (
                        family_counts.get(c["kind"], 0),
                        domain_counts.get(c["domain"], 0),
                        c["status"] != "PENDING",
                        root_counts.get(root(c["id"]), 0),
                        c["id"],
                    )
                )
            else:
                candidates.sort(
                    key=lambda c: (
                        family_counts.get(c["kind"], 0),
                        c["kind"],  # Do not compare unrelated family metric scores.
                        -(c["score"] or 0),
                        domain_counts.get(c["domain"], 0),
                        c["id"],
                    )
                )
            selected = candidates[0]["id"]
            mode = "explore" if explore else "exploit"
            db.execute(
                "INSERT INTO branch_allocations VALUES(?,?,?,?,?)",
                (run_id, key, selected, mode, len(allocations) + 1),
            )
            self.store._event(
                db,
                run_id,
                "branch_allocated",
                {
                    "step_key": key,
                    "hypothesis_id": selected,
                    "mode": mode,
                    "ordinal": len(allocations) + 1,
                    "max_experiments": policy.max_experiments,
                    "max_branch_experiments": policy.max_branch_experiments,
                },
            )
        return selected

    def record(self, run_id: str, identifier: str, report_digest: str) -> None:
        from autodiscover.experiments.registry import evaluate_registered, parse_plan

        report = self.artifacts.get_json(report_digest)
        with self.store.connection(write=True) as db:
            hypothesis = db.execute(
                "SELECT * FROM hypotheses WHERE id=? AND run_id=?", (identifier, run_id)
            ).fetchone()
            if hypothesis is None or hypothesis["kind"] not in ("encoding", "allocation"):
                raise ValueError("Only reviewed executable hypotheses have technical results")
            plan = parse_plan(self.artifacts.get_json(report["plan_digest"]))
            expected_kind = "encoding" if plan.implementation == "encoding-v1" else "allocation"
            if hypothesis["kind"] != expected_kind:
                raise IntegrityError("Hypothesis and experiment family disagree")
            if plan.hypothesis_id != hypothesis["identity"]:
                raise IntegrityError("Evaluation belongs to a different hypothesis")
            if plan.digest != report["plan_digest"] or not report.get("raw_artifact_digest"):
                raise IntegrityError("Evaluation missing preregistration or raw evidence")
            if expected_kind == "allocation" and not db.execute(
                "SELECT 1 FROM experiment_jobs WHERE run_id=? AND plan_digest=? "
                "AND replication=? AND artifact_digest=? AND status='COMPLETED'",
                (run_id, plan.digest, report["replication"], report["raw_artifact_digest"]),
            ).fetchone():
                raise IntegrityError("Evaluation missing completed allocation job in this run")
            raw = self.artifacts.get_json(report["raw_artifact_digest"])
            independent = evaluate_registered(plan, raw, replication=report["replication"])
            if any(report.get(k) != value for k, value in independent.items()):
                raise IntegrityError("Branch verdict disagrees with independent evaluation")
            if db.execute(
                "SELECT 1 FROM branch_results WHERE run_id=? "
                "AND hypothesis_id=? AND report_digest=?",
                (run_id, identifier, report_digest),
            ).fetchone():
                return
            db.execute(
                "INSERT INTO branch_results VALUES(?,?,?,?)",
                (run_id, identifier, report_digest, int(report["passed"])),
            )
            failed = (
                db.execute(
                    "SELECT 1 FROM branch_results WHERE run_id=? AND hypothesis_id=? AND passed=0",
                    (run_id, identifier),
                ).fetchone()
                is not None
            )
            status = "FAILED" if failed else "PROMISING"
            metric_score = (
                report["heldout_min_savings"]
                if hypothesis["kind"] == "encoding"
                else report["heldout_min_gain"]
            )
            score = min(
                metric_score,
                hypothesis["score"] if hypothesis["score"] is not None else metric_score,
            )
            db.execute(
                "UPDATE hypotheses SET status=?,score=? WHERE id=? AND run_id=?",
                (status, score, identifier, run_id),
            )
            self.store._event(
                db,
                run_id,
                "branch_evaluated",
                {
                    "hypothesis_id": identifier,
                    "report_digest": report_digest,
                    "passed": report["passed"],
                    "score": score,
                    "status": status,
                },
            )

    def revise(self, run_id: str, parent_id: str, evidence_id: str) -> str:
        parent = self.get(run_id, parent_id)
        if not isinstance(parent, Hypothesis) or parent.algorithm != "identity":
            raise SearchStopped("NO_REVIEWED_REVISION")
        data = parent.model_dump(mode="json")
        data.update(
            algorithm="rle",
            parent_id=parent_id,
            revision_reason=f"Independent failure {evidence_id}: identity gives no savings; "
            "test reviewed RLE while preserving data, comparator and threshold",
        )
        return self.register(run_id, Hypothesis.model_validate(data), evidence_id=evidence_id)

    def stop(self, run_id: str, reason: str) -> None:
        if not reason.replace("_", "").isalnum() or len(reason) > 100:
            raise ValueError("Machine stopping code required")
        self.policy(run_id)
        with self.store.connection(write=True) as db:
            db.execute(
                "UPDATE director_state SET stopped_reason=? WHERE run_id=?", (reason, run_id)
            )
            self.store._event(db, run_id, "search_stopped", {"reason": reason})

    def tree(self, run_id: str) -> dict[str, Any]:
        with self.store.connection() as db:
            nodes = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM hypotheses WHERE run_id=? ORDER BY depth,id", (run_id,)
                )
            ]
            allocations = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM branch_allocations WHERE run_id=? ORDER BY ordinal", (run_id,)
                )
            ]
            state = db.execute("SELECT * FROM director_state WHERE run_id=?", (run_id,)).fetchone()
        return {
            "nodes": nodes,
            "allocations": allocations,
            "policy": json.loads(state["policy_json"]) if state else None,
            "stopped_reason": state["stopped_reason"] if state else None,
            "novelty": "unknown",
            "commercial_validation": "unvalidated",
        }

    def has_work(self, run_id: str) -> bool:
        tree = self.tree(run_id)
        if not tree["policy"] or tree["stopped_reason"]:
            return False
        policy = SearchPolicy.model_validate(tree["policy"])
        if len(tree["allocations"]) >= policy.max_experiments:
            return False
        nodes = {node["id"]: node for node in tree["nodes"]}

        def root(identifier: str) -> str:
            while nodes[identifier]["parent_id"]:
                identifier = nodes[identifier]["parent_id"]
            return identifier

        counts: dict[str, int] = {}
        for allocation in tree["allocations"]:
            identifier = root(allocation["hypothesis_id"])
            counts[identifier] = counts.get(identifier, 0) + 1
        return any(
            n["kind"] in ("encoding", "allocation")
            and n["status"] in ("PENDING", "PROMISING")
            and counts.get(root(n["id"]), 0) < policy.max_branch_experiments
            for n in tree["nodes"]
        )
