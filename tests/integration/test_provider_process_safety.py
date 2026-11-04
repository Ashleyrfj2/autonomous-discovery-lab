"""Use spawned local mock processes to exercise SQLite dispatch fencing."""

import multiprocessing
import os
from decimal import Decimal
from pathlib import Path

import pytest

from autodiscover.evidence.chain import verify_chain
from autodiscover.models.contracts import GenerationRequest
from autodiscover.models.providers import MockProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.store import Store
from autodiscover.security.budget import Budget, BudgetError

REQUEST = GenerationRequest(prompt="process dispatch fixture")
COST = Decimal("0.03")


class BoundedMock(MockProvider):
    name, model, is_live = "bounded-mock", "fixture", False

    def estimate_cost(self, request):
        return COST

    def generate(self, request):
        return super().generate(request).model_copy(update={"cost_usd": COST})


def _attempt(root: Path, run: str, start, release, reports) -> None:
    class WaitingMock(BoundedMock):
        def generate(self, request):
            reports.put(("dispatch", run))
            if not release.wait(10):
                raise RuntimeError("Test coordinator did not release mock dispatch")
            return super().generate(request)

    router = Router(Store(root, initialize=False), {"review": [WaitingMock()]})
    start.wait(timeout=10)
    try:
        router.generate(run, "review", REQUEST, key="stable")
    except BudgetError as error:
        reports.put(("denied", str(error)))
    else:
        reports.put(("completed", run))


def _die_after_dispatch(root: Path, run: str) -> None:
    class InterruptedMock(BoundedMock):
        def generate(self, request):
            os._exit(17)

    Router(Store(root, initialize=False), {"review": [InterruptedMock()]}).generate(
        run, "review", REQUEST, key="stable"
    )


@pytest.mark.parametrize("same_request", [True, False])
def test_reservations_fence_competing_processes(tmp_path, same_request):
    context = multiprocessing.get_context("spawn")
    store = Store(tmp_path)
    policy = {"max_cost_per_day_usd": "0.05"}
    first = store.create_run("first", policy)
    second = first if same_request else store.create_run("second", policy)
    start, release, reports = context.Barrier(2), context.Event(), context.Queue()
    workers = [
        context.Process(target=_attempt, args=(tmp_path, run, start, release, reports))
        for run in (first, second)
    ]
    for worker in workers:
        worker.start()
    try:
        outcomes = [reports.get(timeout=10) for _ in workers]
        if same_request:
            assert {kind for kind, _ in outcomes} == {"dispatch", "denied"}
            # The losing process can see the hold during the cache read or at reservation.
            assert dict(outcomes)["denied"] in {
                "Prior request incomplete or failed; explicit reconciliation required",
                "Request already reserved; reconcile rather than replay",
            }
        else:
            assert set(outcomes) == {("dispatch", first), ("dispatch", second)}
        release.set()
        dispatched = {run for kind, run in outcomes if kind == "dispatch"}
        assert {reports.get(timeout=10) for _ in dispatched} == {
            ("completed", run) for run in dispatched
        }
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
    finally:
        release.set()
        for worker in workers:
            if worker.is_alive():
                worker.kill()
            worker.join(timeout=5)
        reports.close()
    budget = Budget(store)
    assert sum(budget.totals(run)["requests"] for run in {first, second}) == len(dispatched)
    assert all(budget.totals(run)["settled_usd"] == "0.03" for run in dispatched)
    verify_chain(store)


def test_restart_after_process_death_retains_hold_and_blocks_dispatch(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("process restart", {})
    context = multiprocessing.get_context("spawn")
    child = context.Process(target=_die_after_dispatch, args=(tmp_path, run))
    child.start()
    try:
        child.join(timeout=10)
        assert child.exitcode == 17
    finally:
        if child.is_alive():
            child.kill()
        child.join(timeout=5)

    fixture = BoundedMock()
    reopened = Store(tmp_path, initialize=False)
    router = Router(reopened, {"review": [fixture]})
    with pytest.raises(BudgetError, match="explicit reconciliation required"):
        router.generate(run, "review", REQUEST, key="stable")
    assert len(fixture.responses) == 1
    totals = router.budget.totals(run)
    assert totals["requests"] == 1 and totals["reserved_usd"] == "0.03"
    verify_chain(reopened)
