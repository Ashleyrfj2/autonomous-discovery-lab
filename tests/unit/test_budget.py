from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, nano


def test_reservations_unknown_usage_and_rounding(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("accounting", {})
    budget = Budget(store)
    first = budget.reserve(run, "candidate:0", "fingerprint", Decimal("90"), "mock", "fixture")
    budget.settle(first, None)
    second = budget.reserve(run, "candidate:1", "fingerprint", Decimal("20"), "mock", "fixture")
    budget.settle(second, Decimal("20"))
    assert budget.totals(run)["charged_usd"] == "110"
    assert budget.totals(run)["uncertain_usd"] == "90"
    assert nano(Decimal("0.0000000001")) == 1
    for invalid in (Decimal("NaN"), Decimal("-1")):
        with pytest.raises(ValueError):
            nano(invalid)


def test_concurrent_accounting_across_runs_ignores_legacy_daily_limit(tmp_path):
    store = Store(tmp_path)
    policy = {"max_cost_per_run_usd": "0.1", "max_cost_per_day_usd": "0.1"}
    with store.connection(write=True) as db:
        day = db.execute("SELECT date('now')").fetchone()[0]
        db.execute("INSERT INTO daily_limits VALUES (?,?)", (day, 1))
    runs = [store.create_run(str(i), policy) for i in range(8)]
    budget = Budget(store)

    def reserve(run):
        reservation = budget.reserve(run, "key", run, Decimal("6"), "mock", "fixture")
        budget.settle(reservation, Decimal("7"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(reserve, runs))
    assert sum(Decimal(budget.totals(r)["charged_usd"]) for r in runs) == Decimal("56")
    assert all(store.get_run(r)["status"] == "ACTIVE" for r in runs)
    verify_chain(store)


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
