PHASE: 9 / P9-CONTROL and P9-REVIEW backend
STATUS: LOCALLY_VERIFIED backend tasks; Phase9 dashboard/browser qualification incomplete

IMPLEMENTED:
- Authenticated run pause/resume/cancel with version/fence preconditions, stable request UUID, atomic evidence audit/state mutation and cached original receipts. Cancel requires matching run confirmation; resume never starts workers, raises budgets or authorizes paid calls.
- Read-only source-bound opportunity/evidence review context, explicit source/evidence confirmation, authenticated operator authority, cursor/content-digest guards, atomic source validation/review commit, idempotent review IDs and append-only withdrawal. Client actor/policy overrides and recognizable credentials in rationale are rejected. Synthetic evidence remains excluded even for authenticated review.
- Existing Store/Market CLI behavior retained; HTTP mutation storage requires existing schema and never initializes or migrates a root. Scientific verdicts, budgets, plans and provider permissions are not editable through these endpoints.

VERIFIED:
- uv run ruff check .: passed.
- uv run pyright:0 errors/warnings/information.
- uv run pytest -q:175 passed in16.90 seconds. One upstream Starlette TestClient httpx deprecation warning remains unsuppressed.
- uv build: wheel and source distribution succeeded.
- Six new control tests: duplicate/stale/reused commands, cancellation identity, CSRF/role/policy rejection, concurrent one-event commit, recovery after lost post-commit checkpoint, and authenticated interruption of an actual native worker followed by preserved-stage recovery.
- Six new review tests: explicit confirmation and withdrawal, replay/no duplicate attestations, stale cursor/digest/source rejection, ownership, credential/role rejection, synthetic exclusion and a separate SQLite writer probe proving source validation runs under the review writer lock. Positive classifications are local contract fixtures, not real market evidence.
- Fresh shared-engine regression: eight workflows/96 committed stages/24 independently recomputed jobs, two stage workers, peak1 experiment,3.738991 seconds; zero research-provider cost (mock only).78 targeted Phase8 tests passed. Hash-chained evidence/projections and73 content-addressed artifacts retained.

SOURCE MANIFEST: acf0e0aca2cd9b3dbf8fb3e8f7a05af88ef742fc2e76e2c7fa51e158920568a6
EVIDENCE: phase-9-backend-regression/ contains exact commands/UTC times/results/source hashes, bounded-operation record, JUnit and retained snapshot/CAS. Source manifest rechecked unchanged after qualification.
DECISIONS: DEC-018, DEC-019

DESIGN STATUS: User authorized at most three minutes of12ui design workflow. Four candidates generated; all inspected; referenceA selected. HTML conversion was interrupted at177.066626 seconds (exit -15) while resolving planner output; no HTML completion reported. Selected image and sanitized provenance are in docs/design/. Full candidate/run records stay in ignored runtime/phase9-design and original temporary12ui run directory. No further design calls were started after the allowance. Draft sample data are illustrative and never served as actual research. Four design slots were dispatched; monetary debit was not verified. This is distinct from zero-cost mock research qualification.

REMAINING: Completed design export, UI login/overview/detail/tree/evidence/resources/control/review interactions, responsive/accessibility/visual verification and end-to-end browser acceptance. Full Phase9 is not accepted. No production, distributed, live-inference, scientific novelty or real-demand claim.
NEXT EXACT ACTION: With an extended design allowance, inspect/resume the existing12ui conversion rather than generate another draft; integrate its export against the verified endpoints, then perform browser/visual and shared-engine regression checks. Preserve user file PROJECT_STATUS_REPORT_.md.
