# Meta timeout repair and medium-reasoning qualification preparation — 2026-11-04

Status: LOCALLY VERIFIED (committed-state acceptance follows below) on `integration/ai-native-discovery`, recovered clean published `5f61cf52fbc8aad6e14e05a7663f7416b35fe58e` (remote fetched and equal). Scope: current user request; REQ-AI-004/006, REQ-006/012/014–016. No live inference, deployment, merge or 90-minute launch authorized in this task.

## Recovery and preserved evidence

Both original live qualifications are read-only historical evidence and must never be resumed: `session-4374c2fa7c8f44708fef506893831998` in `runtime/controlled-live` (117 files) and `session-4c376b05f4e8440aab2d15c30a603ec8` in `runtime/controlled-capability-wRPtYg` (10 files). Original files, sidecars and artifacts were SHA-256 inventoried before work and copied to `runtime/meta-medium-preparation/historical-copies/` for inspection. Inventory: `runtime/meta-medium-preparation/historical-before.json`.

Second qualification: first planning call, Spark 1.3, medium, 4,096 completion cap, 30s caller, PAUSED / REQUEST_RECONCILIATION_REQUIRED. Local reservation `a0bca7a6-91a3-4b90-9e63-91b3b4afaa75`, key `discovery-v2:plan:0`, child `discovery-3c2fc77f741841abc9099e464276c8443abedc5e19abdbbc60a764e0b3cad4ad`; UNCERTAIN $0.077408, no reported usage. Fifteen-event anchor `43dc8e65ce8ab1a32f42df08f22a876fdf2c79e82d477a7d29fdf7b3dfc35ee7`. Unknown whether processed/billed. Local `charged_usd` includes conservative holds and is not a provider charge. Do not settle, clear, modify or retry this request.

## Decision and acceptance plan

Create new `*-medium-v2.json` discovery/session/provider files. Planning/extraction low, gap/proposal/independent critique medium. AI suitability and mechanistic analysis share the proposal call, preserving substantive analysis and all scientific/provenance gates. Candidate timeouts 90/45/60/90/90s; provider bound 90s. Branch 1,200s, qualification 3,000s for two branches plus up to 600s review overhead. Keep completion caps 4,096/4,096/4,096/8,192/8,192 including hidden reasoning; no output-length failure established. Retain no retries, durable ledger, null optional dollar ceiling. Worst serial model wait 945s plus fourteen indexed fetches at 8s = 1,057s before local overhead. The enforced branch/session deadlines can always stop earlier.

Acceptance: real Meta adapter path through HTTP mocks for each override/transport timeout, slow success, HTTP and caller timeout, cancellation/interruption, strict responses, identity/token accounting, durable uncertain holds and exact replay; complete offline Discovery-v2 capability session; Ruff/Pyright/full and focused pytest/build; copied history replay and original-file preservation. No claim that medium is superior without comparative live evidence.

## Verification boundary — initial fixture correction

Ten new tests passed. Initial lint found formatting and Pyright found a test-only optional-member narrowing error; corrected. Ruff/Pyright/build subsequently passed. First full run: 378 passed, two historical-fixture setup errors (unknown discovery ID), one existing Starlette/httpx deprecation warning. The selected `historical` root was the earlier live attempt, not the required `historical-retry` packet. Preserved initial full logs/XML, copied the correct retry archive to a new local directory and reran those historical checks before repeating full acceptance. No source gate or historical evidence was changed to accommodate this setup error.

Separate CLI dry-run/resume/report and all-child cache replay completed in fresh `runtime/medium-v2-offline-wdvkw10n`: two closed branches, 12 mock calls, 1,200 input / 960 inclusive output / 180 reasoning tokens, three proposed hypotheses, one substantive authored independent critique, no unresolved reservations, $0. CLI dry-run deliberately shortens the duration to 90s; a full-profile session is also exercised via the simulated slow HTTP adapter test. These are offline structural checks, not live duration, semantic quality or model qualification.

## Local acceptance and exact operating envelope

- New tests: 10 passed, including complete real-adapter HTTP-mocked qualification (both branches, valid first checkpoint/resume, provisional critique, exact replay), actual httpx timeout extensions, 31s virtual slow responses, HTTP/caller timeout, transport interruption, cancellation, strict schema rejection, identity mismatch, reasoning-only output and durable holds/cache rejection. Late responses do not settle unknown holds. Existing separate-process abrupt-death and reservation tests also passed.
- Full suite: **380 passed, 0 failed/errors/skipped in 40.40s**, all four optional evidence inputs configured. Focused provider/discovery/capability/session/budget/quality: **196 passed in 23.45s**. Ruff passed, Pyright 0 errors/warnings, wheel/sdist built. One pre-existing Starlette/httpx deprecation warning remains. Initial failed fixture selection and its logs are retained above.
- CLI: preflight, fresh-root dry-run, first checkpoint/status, resume, report and all-child cache-only replay passed. All 11 runbook shell blocks parsed; four embedded Python inspection/replay snippets executed successfully on copies/mock roots. Paid launch commands were syntax-checked only. No authenticated catalog or billing account check was performed in this repair.
- Preservation: **117/117 first qualification files and 10/10 failed qualification files byte-identical**, including WAL/SHM, checkpoints, logs and artifacts. All four original capability discovery/provider/qualification/90-minute profiles byte-identical to base5f61cf5. Only copied historical roots were opened for SQLite inspection/tests. The original hold/status, 15-event failure anchor and first historical packet/109-event anchor remain unchanged.
- Credential checks: added-line/new-file recognizable-credential scan passed; no credential files or values copied or logged. No paid inference, retry of either historical session, merge, deployment, outreach or 90-minute launch.

Machine acceptance receipt: [meta-medium-local-acceptance.json](meta-medium-local-acceptance.json), including tested code/config hashes, original inventory digests, test counts, rehearsal receipt and raw-log hashes. Full raw logs/XML, failed attempt, copies, old request metadata and atomic checkpoint/event history remain in runtime/meta-medium-preparation and runtime/{checkpoints,logs}/development*.

| Stage | Model | Reasoning | Inclusive completion cap | Effective caller/httpx bound |
| --- | --- | --- | ---: | ---: |
| Planning | muse-spark-1.3 | low | 4,096 | 90s |
| Extraction | muse-spark-1.3 | low | 4,096 | 45s |
| Gap identification | muse-spark-1.2 | medium | 4,096 | 60s |
| AI suitability/mechanistic analysis | muse-spark-1.2 | medium | 8,192 | 90s |
| Hypothesis generation (same proposal call) | muse-spark-1.2 | medium | 8,192 | 90s |
| Independent critique | muse-wonder-1.0 | medium | 8,192 | 90s |

New profiles use the existing capability-v1 schema; v2 in the filenames is the qualification configuration revision, not a changed discovery protocol. Provider reasoning defaults remain minimal/minimal/low; only the new provider timeout bound changes to90s. Preflight rejects pairing the new stage profile with the old45s manifest before dispatch. The only runtime repair passes request-local timeout to httpx operations; it preserves caller timeout, ledger registration/settlement and background-transport ambiguity handling.

A branch reserves up to624,000 input +77,824 completion =701,824 tokens / **$1.893824**. Qualification maximum: two branches /26 attempts /1,248,000 input +155,648 inclusive completion =**1,403,648 tokens / $3.787648**, concurrency1, retries0, branch1,200s, session3,000s. This is unchanged cost because reasoning effort does not reduce the inclusive hard cap. Spark standard input/output rates $1.25/$4.25 per million and Wonder $4/$20 were rechecked against [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits); hidden reasoning counts within output as documented in [Meta reasoning](https://dev.meta.ai/docs/reasoning). No credit/cache discounts or provider tool calls assumed. No dollar caps restored. The historical unresolved $0.077408 is additional exposure, not reconciled or included in the new estimate. All estimates are local gross upper envelopes, not invoices.

The exact old reservation window is **2026-11-04 22:03:37.046029–22:04:07.060981 UTC**; remote processing could continue later. No provider request ID was captured. The runbook supplies metadata extraction, dashboard/request-record/support correlation instructions and explicit unresolved disposition. Account-owner provider evidence remains unavailable; the local hold must remain untouched. The first session's separate local $0.012262 also does not establish provider-confirmed billing.

## Next milestone and remaining uncertainty

Offline implementation/regression: PASS. New controlled Meta qualification: **prepared for separately authorized operator execution only, NOT RUN**. First investigate/document the old ambiguous request; if unconfirmed retain it as unresolved and disclose it before any new authorization. Require substantive real-provider independent critique, verified provenance, settled local usage, valid checkpoint/resume and exact replay for the new test. No automatic rerun if it produces no hypothesis or times out. 90-minute live session: DEFERRED, its frozen profile is unchanged. Unattended overnight: NO-GO.

Real reasoning latency, completion sufficiency, source semantics, provider processing/billing, medium comparative quality and commercial/scientific validity remain unverified. Mocked HTTP and fixture critique establish executable structure/safety only. Exact Terminal commands for preflight, offline rehearsal, new-root launch, checkpoint, reasoning usage, uncertain requests, resume, all-child replay and final report are in [LONG_SESSION_RUNBOOK.md](../LONG_SESSION_RUNBOOK.md). Do not start a paid test during this repair.
