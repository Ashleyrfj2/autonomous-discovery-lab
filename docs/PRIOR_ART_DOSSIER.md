# Source-bound prior-art dossier

Status: **IMPLEMENTED_UNVERIFIED** on the chat-mode branch. This is a read-only review aid, not an automated novelty adjudicator or a completed cross-domain discovery gate. It extends REQ-003, REQ-019, REQ-020, REQ-021, REQ-034 and REQ-037 without replacing current Stage ASSESS output.

## Purpose and boundaries

The existing lab retrieves Crossref metadata and bounded primary documents, preserves original source digests, and retains novelty as unknown. A hypothesis needs more than title matching before anyone can reasonably compare mechanisms. The `prior-art-dossier` command binds candidate statements to exact source passages, records possible overlaps and missing evidence, and returns a proposal for independent scientific review.

It **does not perform searches**, contact publishers, make API/model calls, update the run, attest that a quoted result is true, establish functional equivalence, or change novelty from `unknown`. An empty search or a model-generated comparison is not proof of novelty. Mechanism judgments in request files are treated as unverified assertions, even when their quotation matches the source byte-for-byte.

Reads use a single verified, query-only SQLite snapshot (SnapshotStore) and existing content-addressed source metadata. A changed/invalidated source, wrong run, absent quotation, duplicate comparison or recognizable credential causes refusal. The command sanitizes stdout and does not persist dossier data or make a research-stage transition.

## Running it

1. Choose a run whose prior-art sources are already registered, and obtain a source ID from the persisted evidence records.
2. Create a local JSON request outside Git (example below). Quotations must match actual extracted source text exactly; titles and abstract metadata alone do not establish method details.
3. Run:

```sh
uv run autodiscover --root runtime prior-art-dossier RUN_ID prior-art-request.json
```

4. Save the JSON stdout to **private/retained research evidence storage**, not a public repository if it includes copyrighted/private quotations. Preserve the run and `evidence_cursor` together with the source digest; re-run after any source update. Independently verify the full paper, the method and differences before proposing a novelty verdict.

Example request (source ID is illustrative, **not a valid existing source**):

```json
{
  "schema_version": 1,
  "candidate_id": "H-001",
  "hypothesis": "A measured method reduces errors against a preregistered baseline.",
  "claimed_mechanism": "An adaptive policy uses verification failures to choose further checks.",
  "falsifiable_prediction": "On withheld tasks the policy produces fewer errors than the static baseline.",
  "search_queries": [
    "adaptive verification failure-driven research control",
    "active learning scientific experiment selection"
  ],
  "comparisons": []
}
```

To record a real comparison, add an item to `comparisons` with `source_id`, `quote`, `relationship` (`possible_functional_overlap`, `possible_difference`, `contradictory_finding`, or `background_only`), and `explanation`. Only a source actually attached to this run may be used.

The output is **not a complete literature search record**: proposed queries have `searches_executed_by_this_command: 0`, the coverage is `exhaustive: false`, and `assessment.novelty` remains `unknown`.

## Review acceptance protocol (outside this command)

- Establish explicit scope: candidate mechanism, claim, predicted metric, prior-work cutoff, search date, sources/database coverage and search strings.
- Retrieve full methods and original results when legal/accessible; quote exact supporting and contradicting passages with URL/DOI, author/year, population and method. Track inaccessible sources as limitations rather than absent findings.
- Compare **functions and causal mechanisms**, not brand names or superficial wording. Record the strongest equivalent technique and the strongest disconfirming source.
- Ask an independent reviewer to inspect claimed differences, matching controls, populations, measurement validity and any negative results. Record dissent and uncertainty. Do not translate operator/model assertions into verified novelty.
- Preregister an experiment with a matched baseline, locked metric, held-out data and stopping rule. Preserve all attempts, resource usage and negative outputs to deter post-hoc selection bias.
- Route any startup opportunity through separate real-buyer/problem/payment gates. Literature relevance, benchmark improvement and a plausible industry do not qualify as demand.

## Checks to run on the user's Mac before accepting

```sh
uv run ruff check .
uv run pyright
uv run pytest -q tests/unit/test_prior_art.py tests/integration/test_research_intelligence.py
uv run pytest -q
uv build
```

Also manually compare `prior-art-dossier` output against the same registered source in the evidence view, prove that a read leaves DB/event/report bytes unchanged, and rerun after invalidating a source. GitHub Actions alone is not the merge gate. Because ChatGPT cannot execute the private Mac runtime, local/full validation, exact source-manifest qualification and acceptance remain pending.

## Further work

The next higher-value capability is **actual method-level retrieval and search-log preservation**, followed by independent candidate/evaluator review and tests against contamination-resistant real scientific tasks. The command here is deliberately a safe, small prerequisite; it must not be misreported as Phase 9 dashboard completion or cross-industry scientific discovery.

## External-source integrity

`primary_document_comparisons` counts only currently valid full-text sources with `live_https` or `operator_document` provenance. Metadata, fixtures, and legacy-unverified records are still shown as quotations for debugging but do not count as eligible external method comparisons. Re-labeling the same passage as two different relationships is rejected as duplicate evidence. A qualifying external document still does not establish the scientific truth of a quote or certify novelty.
