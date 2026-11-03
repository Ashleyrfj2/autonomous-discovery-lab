import pytest

from autodiscover.orchestrator.loops import LoopDetected, ProgressGuard, validate_dependencies
from autodiscover.orchestrator.store import Store


def test_circular_dependencies_fail_and_dag_passes():
    validate_dependencies({"discover": [], "research": ["discover"], "design": ["research"]})
    with pytest.raises(LoopDetected):
        validate_dependencies({"a": ["b"], "b": ["a"]})
    with pytest.raises(ValueError):
        validate_dependencies({"a": ["missing"]})


def test_repeated_work_guard_survives_restart(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("loop guard", {})
    for index in range(3):
        reason = ProgressGuard(Store(tmp_path)).observe(
            run, "provider-errors", state="RESEARCH", signature="same timeout", repeat_limit=3
        )
        assert reason == ("REPEATED_IDENTICAL_WORK" if index == 2 else None)
    assert ProgressGuard(store).observe(
        run, "provider-errors", state="DESIGN", signature="different"
    )


def test_oscillation_stagnation_and_token_waste_detected(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("different loops", {})
    guard = ProgressGuard(store)
    reason = None
    for index, state in enumerate(["A", "B", "A", "B", "A", "B"]):
        reason = guard.observe(
            run, "oscillation", state=state, signature=str(index), repeat_limit=10
        )
    assert reason == "STATE_OSCILLATION"
    for index in range(4):
        reason = guard.observe(
            run, "stagnation", state="GENERATE", signature=str(index), progress=1
        )
    assert reason == "NO_MEASURABLE_IMPROVEMENT"
    guard.observe(run, "tokens", state="GENERATE", signature="a", tokens=0)
    assert (
        guard.observe(run, "tokens", state="GENERATE", signature="b", tokens=11, token_limit=10)
        == "TOKEN_CONSUMPTION_WITHOUT_PROGRESS"
    )


def test_replayed_observation_does_not_create_false_loop_after_crash(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("idempotent observations", {})
    for _ in range(6):
        assert (
            ProgressGuard(Store(tmp_path)).observe(
                run,
                "generate",
                state="HYPOTHESIZE",
                signature="same completed generation",
                observation_key="version:2",
            )
            is None
        )
    with pytest.raises(ValueError, match="different work"):
        ProgressGuard(store).observe(
            run,
            "generate",
            state="HYPOTHESIZE",
            signature="changed hypothesis",
            observation_key="version:2",
        )
