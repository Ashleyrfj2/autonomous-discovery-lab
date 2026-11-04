"""Authored synthetic capability fixtures. Never external scientific or market evidence."""

from urllib.parse import parse_qs, urlsplit

from autodiscover.models.contracts import Provider
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import Store
from autodiscover.research.discovery import ROLES, Discovery
from autodiscover.research.retrieval import Fetched
from autodiscover.research.session_rehearsal import RehearsalProvider

SOURCE = "In this synthetic fixture, causal graphs detected inconsistent sensor explanations."
TARGET = (
    "In this synthetic fixture, maintenance operators could not reconcile conflicting "
    "audio and vibration observations using available monitoring tools."
)
PRIOR = "The synthetic baseline uses independent threshold alarms and a human maintenance review."


class CapabilityArchive:
    def fetch(self, url: str) -> Fetched:
        parsed = urlsplit(url)
        query = parse_qs(parsed.query).get("query.bibliographic", [""])[0]
        kind = next((k for k in ("source", "target", "prior") if query.startswith(k)), None)
        items = []
        if kind:
            passage = {"source": SOURCE, "target": TARGET, "prior": PRIOR}[kind]
            items = [
                {
                    "DOI": f"10.0000/synthetic-{kind}",
                    "title": [f"Synthetic {kind} fixture"],
                    "abstract": passage,
                }
            ]
        body = (
            {"message": {"items": items}}
            if parsed.hostname == "api.crossref.org"
            else {"resultList": {"result": []}}
        )
        return Fetched(
            url,
            url,
            canonical(body).encode(),
            "application/json",
            "2026-11-04T00:00:00Z",
            "fixture",
        )


class CapabilityProvider(RehearsalProvider):
    def answer(self, prompt: dict) -> dict:
        task = prompt["task"]
        if task == "plan":
            tracks = prompt.get("allowed_tracks", ["ai_native", "open_science"])
            directions = []
            for i in range(3):
                d = super().answer(prompt)["directions"][i]
                d.update(
                    question=f"Can causal verification resolve sensor conflicts in case {i}?",
                    first_domain="causal verification",
                    second_domain="industrial maintenance",
                    query=f"sensor conflicts case {i}",
                    track=tracks[i % len(tracks)],
                    track_reason="Investigate a missing capability with sourced needs.",
                    source_query=f"source causal verification case {i} branch {self.branch % 3}",
                    target_query=f"target maintenance case {i} branch {self.branch % 3}",
                    prior_art_query=f"prior sensor approaches case {i} branch {self.branch % 3}",
                    priority={
                        **{
                            k: 4
                            for k in [
                                "gap_importance",
                                "gap_evidence",
                                "ai_suitability",
                                "distinctiveness",
                                "plausibility",
                                "information_gain",
                                "experimental_feasibility",
                                "prior_art_uncertainty",
                                "usefulness",
                                "historical_progress",
                            ]
                        },
                        "research_cost": i + 1,
                        "rationale": "Authored scores; external evidence unverified.",
                    },
                )
                directions.append(d)
            return {"directions": directions}
        if task.startswith("extract"):
            findings = []
            for i, s in enumerate(prompt["sources"]):
                passage = s["excerpt"].removeprefix(s["title"] + ". ")
                findings.append(
                    {
                        "finding_id": f"finding-{i}",
                        "citation": {"source_id": s["source_id"], "quote": passage},
                        "location": s["scope"],
                        "domain": "causal verification"
                        if passage == SOURCE
                        else "industrial maintenance",
                        "method": "Synthetic controlled observation; not a real study.",
                        "observation": passage,
                        "limitations": "Synthetic; transfer and demand unmeasured.",
                    }
                )
            return {
                "findings": findings,
                "gap": "Transfer effectiveness remains untested.",
                "query": "",
            }
        if task.startswith("gap"):
            target_ids = [f["finding_id"] for f in prompt["findings"] if f["observation"] == TARGET]
            return {
                "unmet_need": "Resolve inconsistent multimodal sensor interpretations.",
                "need_finding_ids": target_ids,
                "current_workaround": "Threshold alarms and human review.",
                "root_constraint": "Incompatible interpretations lack shared verification.",
                "constraint_status": "speculative",
                "constraint_finding_ids": [],
                "target_user": "Maintenance investigators",
                "economic_buyer": "Unknown buyer",
                "frequency_and_severity": "Unknown outside synthetic fixture.",
                "demand_evidence": "No external commercial evidence.",
                "ai_capability": "Explain audio and vibration using simulation constraints.",
                "ai_approaches": ["Multimodal models", "Independent verification", "Simulation"],
                "why_ai": "Unstructured multimodal observations may need learned representations.",
                "non_ai_alternatives": ["Threshold alarms", "Rules engine", "Human diagnosis"],
                "ai_advantage": "plausible",
                "ai_advantage_reason": "A falsifiable proposal; measured advantage unknown.",
            }
        if task.startswith("review"):
            out = super().answer(prompt)
            out["claim_assessments"] = [
                {
                    "claim_index": i,
                    "judgment": "supports",
                    "rationale": "The synthetic captured passage explicitly states this premise.",
                }
                for i, c in enumerate(prompt["proposal"]["claims"])
                if c["kind"] == "empirical"
            ]
            out.update(prior_art_status="unknown", prior_art_evidence=[])
            out.update(
                ai_necessity="plausible",
                bridge_plausibility="plausible",
                need_support="supports",
                capability_rationale="Fixture supports an untested comparison.",
            )
            return out
        # Build the full contract, including an independent source and target finding.
        base = super().answer(prompt)
        proposal = base["proposal"]
        findings = prompt["findings"]
        source = next(f for f in findings if f["domain"] == "causal verification")
        target = next((f for f in findings if f["observation"] == TARGET), findings[-1])
        proposal["claims"] = [
            {"text": f["observation"], "kind": "empirical", "finding_ids": [f["finding_id"]]}
            for f in [source, target]
        ]
        proposal["hypothesis"].update(
            problem=prompt["gap_analysis"]["unmet_need"],
            evidence=[source["citation"], target["citation"]],
            mechanism="Independent multimodal explanations constrained by causal graph simulation.",
            rationale="Constrained explanations could expose inconsistent sensor interpretations.",
            metric="Correct conflict resolution rate",
            comparator="Rules engine and expert review",
            falsifier="Reject if gain is below five percentage points on held-out fault cases.",
            validation="Compare simulated faults using blinded adjudication.",
            prior_art=[],
            novelty_claim="Unverified; no exhaustive prior-art search.",
        )
        proposal["bridge"].update(
            source_domain="causal verification",
            target_domain="industrial maintenance",
            source_finding_ids=[source["finding_id"]],
            target_evidence_ids=[target["finding_id"]],
            shared_mechanism="Predict sensor signatures from constrained causal explanations.",
            variables=["Sensor conflict frequency", "Fault classification accuracy"],
            target_outcome_metric="Correct conflict resolution rate",
            comparator="Rules engine and expert review",
            domain_mismatches=["Simulation may omit real machinery confounders."],
            measurable_prediction="Improve correct conflict resolution by five percentage points.",
        )
        proposal["opportunity"] = {
            "version": "ai-opportunity-v1",
            "gap": prompt["gap_analysis"],
            "ai_suitability": prompt["gap_analysis"]["ai_advantage"],
            "ai_reasoning": "Multimodal models could generate falsifiable explanations.",
            "non_ai_challenge": "Compare rules engines and human expertise at matched cost.",
            "component_finding_ids": [source["finding_id"]],
            "unsupported_assumptions": ["Simulator preserves relevant sensor signatures."],
            "technical_dependencies": ["Causal simulator", "Multimodal encoder"],
            "model_and_tool_requirements": "Audio/vibration encoders and independent simulator.",
            "data_requirements": "Labeled conflicting sensor sequences with held-out faults.",
            "model_limitations": "Distribution shift and hallucinated causal explanations.",
            "integration_and_deployment": "Offline advisory workflow with human acceptance.",
            "safety_and_reliability": "Never control machinery; require independent review.",
            "verification_method": "Blinded paired evaluation at fixed false alarm rate.",
            "cost_considerations": "Measure inference and expert review costs; unknown now.",
            "existing_products_and_research": ["Rules engines", "Multimodal fault research"],
            "prior_art_evidence": [],
            "prior_art_status": "unknown",
            "differentiation": "Proposed causal verification; equivalent products may exist.",
            "falsifiable_prediction": "Five percentage point improvement on held-out cases.",
            "evaluation_environment": "Seeded simulator and independently labeled faults.",
            "comparator": "Rules engine and expert review",
            "minimum_meaningful_improvement": "Five percentage points.",
            "next_cheapest_experiment": "Test ten synthetic conflicts before field data.",
            "adoption_barriers": "Unknown field reliability and operator trust.",
            "technical_feasibility": "untested",
            "scientific_novelty": "unverified",
            "commercial_validation": "unvalidated",
            "validation_status": "unverified_idea",
        }
        return base


def rehearsal(store: Store, branch: int) -> Discovery:
    routes: dict[str, list[Provider]] = {r: [CapabilityProvider(r, branch)] for r in ROLES}
    return Discovery(Router(store, routes), CapabilityArchive(), allow_retrieval=True)
