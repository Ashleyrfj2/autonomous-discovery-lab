from copy import deepcopy

import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.evaluator import evaluate
from autodiscover.experiments.runner import run as execute
from autodiscover.hypotheses.director import (
    Director,
    DuplicateHypothesis,
    SearchPolicy,
    SearchStopped,
)
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.orchestrator.store import Store


def candidate(domain="telemetry", **change):
    return Hypothesis.model_validate({**demo_proposal(domain), **change})


def setup(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("multi-candidate research", {})
    return store, run, Director(store)


def measure(director, run, identifier):
    hypothesis = director.get(run, identifier)
    assert isinstance(hypothesis, Hypothesis)
    plan = Plan(
        hypothesis_id=hypothesis.identity,
        algorithm=hypothesis.algorithm,
        data_profile=hypothesis.data_profile,
        minimum_savings=hypothesis.threshold,
    )
    director.artifacts.put_json(plan.model_dump(mode="json"))
    raw = execute(plan, Limits())
    report = evaluate(plan, raw)
    report["raw_artifact_digest"] = director.artifacts.put_json(raw)
    digest = director.artifacts.put_json(report)
    director.record(run, identifier, digest)
    return digest


def test_dedup_run_ownership_and_restart_allocation(tmp_path):
    store, run, director = setup(tmp_path)
    hypothesis = candidate()
    identifier = director.register(run, hypothesis)
    assert director.register(run, hypothesis) == identifier
    with pytest.raises(DuplicateHypothesis) as error:
        director.register(run, candidate("different domain but same experiment"))
    assert error.value.existing_id == identifier
    first = director.select(run, key="prioritize:0")
    recovered = Director(Store(tmp_path))
    assert recovered.select(run, key="prioritize:0") == first
    assert len(recovered.tree(run)["allocations"]) == 1
    another_run = store.create_run("separate run", {})
    assert recovered.register(another_run, hypothesis) == identifier
    assert len(recovered.tree(another_run)["nodes"]) == 1


def test_diversity_and_branch_share_survive_restart(tmp_path):
    store, run, director = setup(tmp_path)
    director.configure(
        run, SearchPolicy(max_experiments=4, max_branch_experiments=2, exploration_fraction=1)
    )
    a = director.register(run, candidate("consumer data"))
    b = director.register(run, candidate("gaming data", data_profile="alternating"))
    first = director.select(run, key="one")
    second = Director(Store(tmp_path)).select(run, key="two")
    assert {first, second} == {a, b}
    director.select(run, key="three")
    director.select(run, key="four")
    assert all(
        sum(x["hypothesis_id"] == h for x in director.tree(run)["allocations"]) == 2 for h in [a, b]
    )
    with pytest.raises(SearchStopped, match="EXPERIMENT_LIMIT"):
        Director(Store(tmp_path)).select(run, key="five")
    with pytest.raises(ValidationError):
        SearchPolicy(max_experiments=5, max_branch_experiments=5)
    with pytest.raises(ValueError, match="cannot change"):
        director.configure(run, SearchPolicy())


def test_failure_revision_has_actual_parent_evidence_and_preserves_criteria(tmp_path):
    store, run, director = setup(tmp_path)
    original = candidate(algorithm="identity")
    parent = director.register(run, original)
    director.select(run, key="parent")
    failure = measure(director, run, parent)
    child = director.revise(run, parent, failure)
    revision = director.get(run, child)
    assert isinstance(revision, Hypothesis)
    assert revision.parent_id == parent
    assert revision.revision_reason is not None
    assert failure in revision.revision_reason
    assert revision.threshold == original.threshold
    assert revision.data_profile == original.data_profile
    assert revision.comparator == original.comparator
    assert revision.algorithm == "rle"
    assert director.select(run, key="revision") == child
    measure(director, run, child)
    assert [n["status"] for n in director.tree(run)["nodes"]] == ["FAILED", "PROMISING"]
    # Child generations cannot reset the root branch's total allocation.
    with pytest.raises(SearchStopped, match="NO_ELIGIBLE"):
        director.select(run, key="bypass-share")
    # Cross-run parent references and invented evidence are rejected.
    other = store.create_run("other", {})
    with pytest.raises(ValueError, match="same run"):
        director.register(other, revision, evidence_id=failure)


def test_unsupported_cross_domain_proposal_remains_theoretical(tmp_path):
    store, run, director = setup(tmp_path)
    proposal = ResearchProposal(
        question="Can a porous surface reduce evaporation?",
        domain="materials science",
        connection_domain="plant physiology",
        prediction="At least 5 percent lower evaporation than a smooth control",
        metric="water-loss-rate",
        unit="grams per hour",
        comparator="smooth surface control",
        direction="decrease",
        minimum_effect=5,
        measurement_protocol="Compare weighed samples under matched humidity and temperature.",
    )
    identifier = director.register(run, proposal)
    assert director.tree(run)["nodes"][0]["status"] == "THEORETICAL"
    assert director.get(run, identifier) == proposal
    with pytest.raises(SearchStopped, match="NO_ELIGIBLE"):
        director.select(run, key="unauthorized-execution")
    with pytest.raises(ValueError, match="Only reviewed"):
        director.record(run, identifier, director.artifacts.put_json({"passed": True}))


def test_forged_positive_branch_score_is_recomputed_and_rejected(tmp_path):
    _, run, director = setup(tmp_path)
    identifier = director.register(run, candidate(algorithm="identity"))
    failure = measure(director, run, identifier)
    forged = deepcopy(director.artifacts.get_json(failure))
    forged.update(passed=True, heldout_min_savings=1)
    digest = director.artifacts.put_json(forged)
    with pytest.raises(IntegrityError, match="independent"):
        director.record(run, identifier, digest)
    assert director.tree(run)["nodes"][0]["status"] == "FAILED"


def test_revision_cannot_lower_threshold_or_switch_to_easier_data(tmp_path):
    _, run, director = setup(tmp_path)
    original = candidate(algorithm="identity", data_profile="alternating")
    parent = director.register(run, original)
    failure = measure(director, run, parent)
    for change in ({"threshold": 0.01}, {"data_profile": "runs"}):
        revision = Hypothesis.model_validate(
            {
                **original.model_dump(),
                **change,
                "algorithm": "rle",
                "parent_id": parent,
                "revision_reason": "claimed improvement",
            }
        )
        with pytest.raises(ValueError, match="cannot weaken"):
            director.register(run, revision, evidence_id=failure)


def test_exploitation_prefers_actual_promising_result(tmp_path):
    _, run, director = setup(tmp_path)
    director.configure(run, SearchPolicy(exploration_fraction=0))
    promising = director.register(run, candidate("consumer"))
    director.select(run, key="first")
    measure(director, run, promising)
    director.register(run, candidate("other", data_profile="alternating"))
    assert director.select(run, key="exploit") == promising
    assert director.tree(run)["allocations"][-1]["mode"] == "exploit"


def test_concurrent_allocation_key_only_spends_one_credit(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    _, run, director = setup(tmp_path)
    identifier = director.register(run, candidate())
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(
            pool.map(lambda i: Director(Store(tmp_path)).select(run, key="same-step"), range(8))
        )
    assert values == [identifier] * 8
    assert len(director.tree(run)["allocations"]) == 1
