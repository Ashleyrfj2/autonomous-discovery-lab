from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from autodiscover.config import Limits
from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, BudgetError, nano


def test_reservations_unknown_usage_and_rounding(tmp_path):
    store = Store(tmp_path)
    run = store.create_run(
        "budget", Limits(max_cost_per_run_usd=Decimal("0.1")).model_dump(mode="json")
    )
    budget = Budget(store)
    reserved = budget.reserve(run, "one", "fingerprint", Decimal("0.09"), "mock", "fixture")
    budget.settle(reserved, None)
    with pytest.raises(BudgetError, match="RUN_BUDGET"):
        budget.reserve(run, "two", "fingerprint", Decimal("0.02"), "mock", "fixture")
    assert budget.totals(run)["charged_usd"] == "0.09"
    assert nano(Decimal("0.0000000001")) == 1
    for invalid in (Decimal("NaN"), Decimal("-1")):
        with pytest.raises(ValueError):
            nano(invalid)


def test_daily_limit_across_runs_and_concurrent_reservations(tmp_path):
    store = Store(tmp_path)
    policy = Limits(max_cost_per_day_usd=Decimal("0.1")).model_dump(mode="json")
    runs = [store.create_run(str(i), policy) for i in range(8)]
    budget = Budget(store)

    def reserve(run):
        try:
            return budget.reserve(run, "key", run, Decimal("0.06"), "mock", "fixture")
        except BudgetError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert len([r for r in pool.map(reserve, runs) if r is not None]) == 1
    assert sum(Decimal(budget.totals(r)["charged_usd"]) for r in runs) == Decimal("0.06")


def test_cost_overrun_pauses_run_and_keeps_actual_usage(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("overrun", {})
    budget = Budget(store)
    identifier = budget.reserve(run, "one", "hash", Decimal("0.01"), "meta", "configured")
    budget.settle(identifier, Decimal("0.02"), usage={"input_tokens": 5})
    assert store.get_run(run)["status"] == "PAUSED"
    assert budget.totals(run)["charged_usd"] == "0.02"
    with pytest.raises(BudgetError):
        budget.reserve(run, "two", "hash", Decimal("0"), "mock", "fixture")


def test_one_request_cannot_consume_other_candidates_cost_allocation(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("fair cost allocation", {})
    budget = Budget(store)
    first = budget.reserve(
        run,
        "candidate:0",
        "hash",
        Decimal("0.3"),
        "mock",
        "fixture",
        request_limit_usd=Decimal("0.4"),
    )
    budget.settle(first, None)
    with pytest.raises(BudgetError, match="REQUEST_ALLOCATION"):
        budget.reserve(
            run,
            "candidate:1",
            "hash",
            Decimal("0.2"),
            "mock",
            "fixture",
            request_limit_usd=Decimal("0.4"),
        )
    budget.reserve(
        run,
        "another-candidate:0",
        "other",
        Decimal("0.4"),
        "mock",
        "fixture",
        request_limit_usd=Decimal("0.4"),
    )
    assert budget.totals(run)["charged_usd"] == "0.7"


def test_late_cost_overrun_cannot_restore_a_cancelled_run(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("cancelled with inference in flight", {})
    budget = Budget(store)
    identifier = budget.reserve(run, "one", "hash", Decimal("0.01"), "meta", "configured")
    store.control(run, "cancel")
    fence = store.get_run(run)["fence"]
    budget.settle(identifier, Decimal("0.02"), usage={"input_tokens": 5})
    assert store.get_run(run)["status"] == "CANCELLED"
    assert store.get_run(run)["fence"] == fence
    assert budget.totals(run)["charged_usd"] == "0.02"
    verify_chain(store)
