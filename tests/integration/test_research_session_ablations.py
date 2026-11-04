"""One-component fixture ablations on Discovery-v2, with no live dispatch."""

from copy import deepcopy

import pytest
from test_research_quality_benchmark import DATA, FrozenResponse, cite, run_pipeline

from autodiscover.orchestrator.durability import canonical
from autodiscover.research import discovery, discovery_quality
from autodiscover.research.discovery_contracts import RecoveryDecision

CASES = {
    "extraction": ["NEG-01", "POS-01", "POS-02"],
    "claim_screen": ["NEG-04", "POS-01"],
    "bridge": ["NEG-02", "POS-03"],
    "recovery": ["POS-04", "NEG-01"],
    "critique": ["NEG-03", "NEG-07", "POS-04"],
    "prior_art": ["NEG-07", "POS-04"],
}


def _measures(report):
    return {
        "retained": sum(c.disposition == "external_review_required" for c in report.candidates),
        "revised": sum(c.revised is not None for c in report.candidates),
        "prior_art": sum(c.scientific_gate.prior_art_identified for c in report.candidates),
        "requests": report.usage["requests"],
        "input_tokens": report.usage["input_tokens"],
        "output_tokens": report.usage["output_tokens"],
    }


@pytest.mark.parametrize("component", CASES)
def test_matched_component_ablation(tmp_path, monkeypatch, component):
    baseline_path = tmp_path / "baseline"
    original_answer = FrozenResponse.answer

    def answer(self, prompt):
        result = original_answer(self, prompt)
        if prompt["task"].startswith("hypothesis") and result.get("proposal"):
            if component == "claim_screen" and self.case["challenge"] == "abstract":
                result["proposal"]["claims"][0]["finding_ids"] = []
            if component == "bridge" and self.case["challenge"] == "exploratory":
                result["proposal"]["bridge"] = None
        return result

    monkeypatch.setattr(FrozenResponse, "answer", answer)
    baseline = {}
    for case_id in CASES[component]:
        _, packet, _, _ = run_pipeline(
            baseline_path / case_id,
            DATA["cases"][case_id],
            "discovery-v2",
        )
        baseline[case_id] = _measures(packet)

    original_screen = discovery_quality.screen_proposal
    original_decision = discovery_quality.decide_recovery
    original_evaluate = discovery.evaluate_quality

    if component in {"claim_screen", "bridge"}:

        def screen(direction, proposal, findings, evidence):
            if component == "claim_screen" and findings:
                proposal = proposal.model_copy(
                    update={
                        "claims": [
                            claim.model_copy(
                                update={
                                    "finding_ids": claim.finding_ids or [findings[0].finding_id],
                                }
                            )
                            for claim in proposal.claims
                        ],
                    }
                )
            if component == "bridge" and proposal.bridge is None:
                direction = direction.model_copy(update={"second_domain": direction.first_domain})
            return original_screen(direction, proposal, findings, evidence)

        monkeypatch.setattr(discovery_quality, "screen_proposal", screen)
    elif component == "recovery":

        def decide(*args, **kwargs):
            result = original_decision(*args, **kwargs)
            return (
                RecoveryDecision(action="inconclusive", reason="Recovery disabled for fixture")
                if result.action == "retrieve"
                else result
            )

        monkeypatch.setattr(discovery_quality, "decide_recovery", decide)

    rows = []
    for case_id in CASES[component]:
        case = DATA["cases"][case_id]
        if component in {"extraction", "critique", "prior_art"}:

            def evaluate(plan, initial, order, generate, *args, case=case):
                def altered(key, role, schema, instruction, **context):
                    if component == "extraction" and key.startswith("extract"):
                        direction = context["direction"]
                        return schema.model_validate(
                            {
                                "findings": [
                                    {
                                        "finding_id": f"F-{i:02}",
                                        "citation": cite(source),
                                        "location": "abstract",
                                        "domain": direction[
                                            "first_domain" if i == 0 else "second_domain"
                                        ],
                                        "method": "Copy the captured excerpt as a finding.",
                                        "observation": cite(source)["quote"],
                                        "limitations": "Interpretation remains unverified.",
                                    }
                                    for i, source in enumerate(context["sources"])
                                ],
                                "gap": "No extraction performed.",
                                "query": "",
                            }
                        )
                    if component == "critique" and key.startswith("review"):
                        body = deepcopy(
                            FrozenResponse("offline", [], case).answer(
                                {
                                    "task": key,
                                    **context,
                                }
                            )
                        )
                        for assessment in body["claim_assessments"]:
                            assessment.update(judgment="supports")
                        for objection in body["objections"]:
                            objection.update(material=False)
                        return schema.model_validate(body)
                    result = generate(key, role, schema, instruction, **context)
                    if component == "prior_art" and key.startswith("review"):
                        return result.model_copy(
                            update={
                                "prior_art_status": "unknown",
                                "prior_art_evidence": [],
                                "objections": [
                                    item.model_copy(update={"material": False})
                                    if item.category == "prior_art"
                                    else item
                                    for item in result.objections
                                ],
                            }
                        )
                    return result

                return original_evaluate(plan, initial, order, altered, *args)

            monkeypatch.setattr(discovery, "evaluate_quality", evaluate)
        _, packet, _, _ = run_pipeline(tmp_path / "ablation" / case_id, case, "discovery-v2")
        row = {
            "component": component,
            "case": case_id,
            "full": baseline[case_id],
            "ablated": _measures(packet),
        }
        rows.append(row)
        print("ABLATION " + canonical(row))

    by_case = {row["case"]: row for row in rows}
    if component == "extraction":
        assert all(row["ablated"]["retained"] == row["full"]["retained"] for row in rows)
        assert all(row["ablated"]["requests"] < row["full"]["requests"] for row in rows)
    elif component in {"claim_screen", "bridge"}:
        case_id = "POS-01" if component == "claim_screen" else "POS-03"
        assert by_case[case_id]["full"]["retained"] == 0
        assert by_case[case_id]["ablated"]["retained"] == 1
    elif component == "recovery":
        assert by_case["POS-04"]["full"]["retained"] == 1
        assert by_case["POS-04"]["ablated"]["retained"] == 0
    elif component == "critique":
        assert by_case["NEG-03"]["full"]["retained"] == 0
        assert by_case["NEG-03"]["ablated"]["retained"] == 1
    else:
        assert by_case["NEG-07"]["full"]["prior_art"] == 1
        assert by_case["NEG-07"]["ablated"]["retained"] == 1
        assert by_case["NEG-07"]["ablated"]["prior_art"] == 0
