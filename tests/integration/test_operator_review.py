from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from autodiscover.commercial.contracts import MarketEvidence
from autodiscover.commercial.service import Market
from autodiscover.orchestrator.lab import Lab
from autodiscover.reporting.web import create_app

ORIGIN = "http://127.0.0.1:8765"


def setup(tmp_path, *, synthetic=False):
    lab = Lab(tmp_path / "runtime")
    run = lab.demo()
    market = Market(lab.store)
    opportunity = lab.report(run)["commercial"]["opportunity_id"]
    if synthetic:
        evidence = market.add_evidence(
            opportunity, MarketEvidence(origin="synthetic", kind="problem_report")
        )
    else:
        path = tmp_path / "contract-fixture.txt"
        quote = "Local contract fixture: a workflow problem described by an operator."
        path.write_text(quote)
        source = market.add_document(run, path, title="Test fixture only; no real buyer evidence")
        evidence = market.add_evidence(
            opportunity,
            MarketEvidence(origin="external", kind="problem_report", source_id=source, quote=quote),
        )
    phrase = SecretStr(str(uuid4()))
    client = TestClient(
        create_app(lab.store.root, phrase), base_url=ORIGIN, client=("127.0.0.1", 9999)
    )
    assert (
        client.post(
            "/api/session", json={"password": phrase.get_secret_value()}, headers={"Origin": ORIGIN}
        ).status_code
        == 200
    )
    headers = {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/session").json()["csrf_token"]}
    return lab, run, market, opportunity, evidence, client, headers


def review_body(client, opportunity, *, accepted=True):
    result = client.get(f"/api/market/{opportunity}/review")
    assert result.status_code == 200
    context = result.json()
    item = context["items"][0]
    return {
        "request_id": str(uuid4()),
        "expected_cursor": context["cursor"]["seq"],
        "evidence_id": item["evidence_id"],
        "confirmation": item["confirmation_text"],
        "review": {
            "accepted": accepted,
            "facts": ["real_problem"] if accepted else [],
            "rationale": "Local test fixture, not actual demand",
            "source_digest": item["source_digest"],
        },
    }


def test_explicit_operator_review_and_withdrawal_are_idempotent_and_preserve_technical_history(
    tmp_path,
):
    lab, run, _market, opportunity, _evidence, client, headers = setup(tmp_path)
    path = f"/api/market/{opportunity}/review"
    before = lab.report(run)
    body = review_body(client, opportunity)
    assert client.post(path, json=body, headers={"Origin": ORIGIN}).status_code == 403
    first = client.post(path, json=body, headers=headers)
    assert first.status_code == 200 and first.json()["assessment"]["level"] == 1
    replay = client.post(path, json=body, headers=headers)
    assert replay.status_code == 200 and replay.json()["review_id"] == first.json()["review_id"]
    changed = {**body, "review": {**body["review"], "accepted": False}}
    assert client.post(path, json=changed, headers=headers).status_code == 409
    withdrawal = review_body(client, opportunity, accepted=False)
    assert client.post(path, json=withdrawal, headers=headers).json()["assessment"]["level"] == 0
    after = lab.report(run)
    assert before["assessment"] == after["assessment"]
    assert after["commercial"]["level"] == after["commercial"]["recorded_level"] == 0
    with lab.store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM market_reviews").fetchone()[0] == 2


def test_review_rejects_missing_confirmation_role_and_credentials(tmp_path):
    lab, _run, _market, opportunity, _evidence, client, headers = setup(tmp_path)
    path = f"/api/market/{opportunity}/review"
    body = review_body(client, opportunity)
    for update in (
        {"confirmation": ""},
        {"confirmation": "automatically approve"},
        {"actor_kind": "human"},
    ):
        assert client.post(path, json={**body, **update}, headers=headers).status_code == 422
    secret_review = {**body["review"], "rationale": "api_key=" + "private-test-sentinel"}
    result = client.post(path, json={**body, "review": secret_review}, headers=headers)
    assert result.status_code == 422 and "private-test-sentinel" not in result.text
    with lab.store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM market_reviews").fetchone()[0] == 0


def test_review_rejects_stale_cursor_replaced_digest_and_invalidated_source(tmp_path):
    lab, run, market, opportunity, evidence, client, headers = setup(tmp_path)
    path = f"/api/market/{opportunity}/review"
    stale = review_body(client, opportunity)
    lab.store.create_run("intervening event", {})
    assert client.post(path, json=stale, headers=headers).status_code == 409
    wrong = review_body(client, opportunity)
    wrong["review"]["source_digest"] = "0" * 64
    wrong["confirmation"] = f"REVIEW {evidence} {'0' * 64}"
    assert client.post(path, json=wrong, headers=headers).status_code == 409
    current = review_body(client, opportunity)
    _, record = market.evidence(evidence)
    assert record.source_id is not None
    market.catalog.invalidate(run, record.source_id, reason="Test source withdrawal")
    assert client.post(path, json=current, headers=headers).status_code == 409
    context = client.get(path).json()
    assert context["items"][0]["confirmation_text"] is None
    assert context["assessment"]["level"] == 0


def test_synthetic_evidence_cannot_be_promoted_even_by_authenticated_review(tmp_path):
    lab, _run, market, opportunity, evidence, client, headers = setup(tmp_path, synthetic=True)
    path = f"/api/market/{opportunity}/review"
    context = client.get(path).json()
    assert context["items"][0]["source_digest"] is None
    body = {
        "request_id": str(uuid4()),
        "expected_cursor": context["cursor"]["seq"],
        "evidence_id": evidence,
        "confirmation": f"REVIEW {evidence} {'0' * 64}",
        "review": {
            "accepted": True,
            "facts": ["real_problem"],
            "rationale": "Attempted synthetic promotion test",
            "source_digest": "0" * 64,
        },
    }
    assert client.post(path, json=body, headers=headers).status_code == 422
    assert market.assess(opportunity)["level"] == 0
    with lab.store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM market_reviews").fetchone()[0] == 0


def test_evidence_cannot_be_reviewed_through_another_opportunity(tmp_path):
    lab, _run, _market, opportunity, _evidence, client, headers = setup(tmp_path)
    another = lab.demo(topic="another workflow")
    other = lab.report(another)["commercial"]["opportunity_id"]
    body = review_body(client, opportunity)
    result = client.post(f"/api/market/{other}/review", json=body, headers=headers)
    assert result.status_code == 422 and result.json()["error"] == "EVIDENCE_OWNERSHIP_MISMATCH"


def test_source_validation_is_inside_the_review_write_transaction(tmp_path, monkeypatch):
    import sqlite3

    import pytest

    from autodiscover.commercial.contracts import HumanReview

    lab, _run, market, opportunity, evidence, client, _headers = setup(tmp_path)
    body = review_body(client, opportunity)
    original = market._external_source
    observations = []

    def check_lock(record):
        probe = sqlite3.connect(lab.store.path, timeout=0, isolation_level=None)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                probe.execute("BEGIN IMMEDIATE")
            observations.append(True)
        finally:
            probe.close()
        return original(record)

    monkeypatch.setattr(market, "_external_source", check_lock)
    market.review(
        evidence,
        HumanReview.model_validate(body["review"]),
        actor_kind="human",
        request_id=body["request_id"],
        expected_cursor=body["expected_cursor"],
    )
    assert observations == [True]
