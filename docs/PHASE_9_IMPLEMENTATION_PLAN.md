# Phase 9 implementation plan — local operator interface

Status: IMPLEMENTATION IN_PROGRESS following user authorization. Read/auth/control/review backend tasks are locally verified. Four design references generated; HTML conversion hit the user's three-minute time limit. Dashboard and browser qualification remain incomplete; no deployment.

Prerequisite satisfied before this plan was written: Phase 8 accepted and committed on main as `e1e5ae78731d3d00e6154e0226326cb9ee74f40b`, message `feat: complete and verify phase 8 durable execution`. Exact qualified source manifest: `58aba75623694c0fbf86b227d7a5a6f95f8e2b054057cad2bb84b2f66bb4fb21`. Acceptance: [Phase 8](phase_reports/phase-8.md), [evidence](phase_reports/phase-8-acceptance/acceptance.json).

## Scope and operator workflow

Implement REQ-031 and the master brief's Phase 9 inspection/control gate within the existing modular monolith. Preserve REQ-002/003/005/006/009/012/013/017/024/034/038. Operator opens the local dashboard, selects a persisted run, sees current work, branches and evidence, inspects independent results and uncertainty, and uses explicit controls or reviews source-bound commercial facts. Every value comes from the selected runtime root. An empty root shows an empty state; no fabricated discoveries, buyers, payments or spend.

Use a small local FastAPI adapter with server-rendered HTML and limited browser JavaScript. No separate frontend framework, infrastructure redesign or distributed worker service is needed for the first implementation. Before adding dependencies, verify official current API/security documentation, pin through uv, and record decisions. Before nontrivial UI creation, load the required 12ui-design skill and follow applicable design workflow; no design-generation or UI implementation has been performed during planning.

## Existing interfaces and proposed read boundary

Existing authoritative interfaces: Store.list_runs/get_run/outputs/control; Lab.report; Director.tree; Jobs.status; Scheduler.status; Catalog sources/claims; Market opportunity/evidence/assess/review; Budget.totals; verify_chain and content-addressed Artifacts.get/get_json. Reuse these contracts and transaction rules. Do not let an HTTP handler set raw database status, verdicts, model configuration or prices.

Lab.report currently also persists a derived JSON file. First extract its aggregation into a shared read service with an explicit persistence option, retaining existing CLI behavior. HTTP GETs must not create runs, change controls or write a report/checkpoint. Use a consistent SQLite read snapshot and event cursor for each response. Verify projections before exposing accepted state; integrity failures show a blocked integrity status with diagnostic metadata, never a fabricated successful report. Recompute current market classification while preserving recorded stage outcomes. A currently invalidated claim must not look accepted because an old report did.

Proposed API contracts (design targets, not available endpoints):

| Interface | Existing source | Response / behavior |
|---|---|---|
| GET /api/runs | Store plus bounded summary read | Run ID/topic, status/stage/version, technical/novelty/current-market classifications, committed steps, conservative spend and updated cursor |
| GET /api/runs/{id} | Shared report read service | Recorded vs current assessments, uncertainty, controls allowed by current state, resource/usage totals |
| GET /api/runs/{id}/tree | Director.tree and authoritative evaluations | Parent/child graph, failed/promising/theoretical states, allocations, evaluation links and stop reason |
| GET /api/runs/{id}/evidence | Catalog, steps/events and verified artifacts | Paginated source/claim/result provenance; valid/invalid reasons; exact source attribution; independent evaluation and replica identities |
| GET /api/runs/{id}/jobs | Jobs.status and accepted raw resource records | Job/replica state, attempt/error counts, worker identity, elapsed/RSS, recovery reason; distinguish retained measurement from current process observation |
| GET /api/queue | Scheduler.status, read only | Dispatch status/ownership, attempts, progress; committed run steps remain authoritative |
| GET /api/runs/{id}/usage | Budget.totals | Settled, reserved, uncertain and conservative charged USD, token counts; no claim of an actual provider invoice |
| POST /api/runs/{id}/control | Store.control through transactional adapter | Allowlisted pause/resume/cancel only, expected version/fence and request identity; conflicts return reload guidance; resume changes durable eligibility and does not silently launch paid work |
| GET /api/market/{id}/review | Market opportunity/evidence/assess | Exact source-bound review context, document digest, evidence facts and missing information |
| POST /api/market/{id}/review | Authenticated explicit operator adapter to Market.review | Source-digest-bound acceptance/withdrawal, attested facts and reason; append-only audit, no synthetic evidence promotion |

Responses must be typed and bounded. Resolve run/opportunity/evidence ownership before access or mutation. Artifact links resolve verified digests through the selected root, never arbitrary filesystem paths. Private operator documents require the operator session; no public URLs, browser third-party assets or analytics. No `.env`, credentials, auth headers, process environments, raw provider exception bodies or unrelated local files reach the browser. Technical success, novelty and market evidence level remain separate fields everywhere.

## Authorization and human review boundary

Default bind: loopback only, one operator and one explicitly selected runtime root. Starting the server is a foreground CLI action, not an installed daemon. Use a fresh local operator session established by an explicit interactive startup action, an HttpOnly same-site cookie, CSRF protection, strict Host/Origin validation and JSON content types for mutations. Bind the session to this process/root; do not accept a client-supplied actor_kind or a bearer token in a URL. Keep session secrets out of logs, persisted reports and model tools. Reject unauthenticated, cross-origin and DNS-rebinding requests. Local browser session access is an authority boundary, not proof that an arbitrary machine is trusted.

GETs have no side effects. Each mutation validates expected version/fence and current policy in the same transaction as its event. A repeated command must not append duplicate accepted evidence; stale commands return conflict. Confirm irreversible run cancellation with run identity visible. Pause/resume preserves existing scientific state and budgets. Dashboard controls must not enable live inference, raise limits, add network origins, execute generated code or bypass preregistered plans.

Market review needs an explicit operator-only interface displaying the exact document digest/quote and a clear attestation. The server derives human authority from the established operator session and requires a fresh source-bound confirmation; a model cannot call an approval tool or supply a role field. Never auto-submit or pre-accept commercial facts. Recheck source validity/digest at submission, reject stale/replaced evidence, and preserve withdrawal history. Tests will model authentication/attestation boundaries; they cannot prove actual interview/payment authenticity. Preserve the CLI's explicit human-review rule; record the browser session extension in a decision before implementation.

No approval needed for ordinary authorized local implementation. Human authorization is required before non-loopback/multi-user exposure, deployment, external messages/buyer outreach, broader permissions, paid inference or new spending limits. Those actions are outside this plan's default scope.

## Screens and interaction states

1. Runs overview: actual active/paused/failed/completed workflows, current stage, technical/novelty/market badges, conservative usage totals, queue contention and integrity warnings. Include empty, loading, stale and error states.
2. Run detail: lifecycle progress and failed/revised paths; side-by-side independent classifications; hypothesis tree linked to experiment/evaluation/replica records. Present theoretical proposals as unexecuted.
3. Evidence detail: provenance, exact quotations, source access/publication metadata, content address, current validity and dependency invalidation; distinguish candidate claims, interpretations and recomputed results. Render all untrusted text as escaped text, never executable HTML/Markdown.
4. Operations panel: queue/jobs, attempts, recovery reasons, observed resources with timestamps, settled/reserved/uncertain spend and limits; pause/resume/cancel controls appropriate to actual run status.
5. Human review panel: opportunity, buyer/user/problem/alternatives, evidence provenance and explicit fact review/withdrawal. Unsupported demand stays level0; positive fixtures appear only in clearly labeled tests.

Start with a readable tree/list and accessible tabular detail; add richer graph interaction only when it improves navigation. Use keyboard-operable controls, clear focus, sufficient contrast, responsive layouts, and text labels alongside color. All interface content describes operator decisions, not internal implementation trivia.

## Polling and resource behavior

Poll active summaries about every two seconds using an event cursor; slower refresh for inactive runs, pause when the page is hidden, and back off on errors. Display last refresh time and stale status; no silent fake live metrics. Request detail/artifacts on demand with pagination/size limits. Avoid launching workers on page load or attaching SSE/WebSockets before a measured need. Existing foreground workers continue independently; HTTP read requests neither extend a worker's authority nor change scheduling.

A single trusted controller owns mutations; short synchronous reads use independent SQLite connections. Do not run a long experiment inside an HTTP request. Preserve Phase 8 ownership/fencing, cooperative cancellation and bounded admission. A local UI session cannot erase uncertain reservations or mark an experiment accepted. If audit cost becomes material, measure before adding caching; cache entries bind to the evidence cursor and invalidation state.

## Dependency-ordered tasks and acceptance

| Task | Work | Acceptance |
|---|---|---|
| P9-READ | Shared typed, bounded read views with explicit non-persisting report mode | Compare responses with actual persisted fixtures; GETs leave DB/events/report files unchanged; corruption blocks accepted output |
| P9-AUTH | Foreground local adapter, operator session, Host/Origin/CSRF protection | Unauthenticated/cross-origin/rebinding/malformed/oversized requests rejected; no credentials exposed; no service deployment |
| P9-VIEW | Overview, run detail, tree/evidence/evaluation/usage/jobs views | Real engine runs populate views; empty/stale/error states correct; original technical/novelty/market distinctions retained |
| P9-CONTROL | Transactional versioned/idempotent pause/resume/cancel adapter | Active-worker control preserves committed stages/replicas; stale or duplicated clicks cannot regain authority or duplicate events |
| P9-REVIEW | Explicit authenticated source-bound review/withdrawal | No client role escalation; invalidated/synthetic evidence cannot qualify; actual demo remains unvalidated; historical vs current levels clear |
| P9-QUALIFY | Browser/API/adversarial checks, retained sanitized evidence and docs | All required local checks plus complete operator flows; final source/artifact identity recorded, limits and remaining mission gaps reported |

First exact implementation step in the next authorized implementation session: read AGENTS and recovery records, inspect Phase 8 commit/source manifest, then implement P9-READ by extracting the existing report aggregation with an explicit no-write mode and typed pagination/cursor contracts. Verify unchanged CLI output and read-only behavior before introducing HTTP or UI dependencies.

## Verification plan

- Unit: serialization, pagination, run/evidence ownership, state-dependent controls, conservative usage categories, stale cursor/version rules and source-digest confirmation.
- API integration: actual temporary SQLite/CAS roots and the real services; read/write isolation; report parity; valid controls; authentication/CSRF/origin/host rejection; duplicate and stale mutations.
- Adversarial: injected retrieved text and filenames cannot execute; path traversal, raw secrets/exception leakage and forged role/verdict fields rejected; invalid source/claim/job projections fail closed; synthetic demand cannot be elevated through the UI.
- Browser: inspect a real completed mock run, a failed/revised branch, active pause/resume/cancel, preserved replication after interruption, budget stop/uncertain spend, invalidated source and review withdrawal; verify persisted effects using the engine after each interaction. No UI-only arrays may satisfy this gate.
- Visual/accessibility: inspect desktop and narrow layouts, tree navigation, keyboard/focus, overflow/long source text, empty/error states; retain sanitized screenshots. Use mandatory design skill before substantive UI creation.
- Regression/release: Ruff, Pyright, full pytest and build; rerun relevant Phase 8 recovery/concurrency qualification if shared engine code changes. Distinguish API fixture tests, actual local browser flows, public retrieval, live inference and production readiness. Record new dependency/authority decisions and update all persistent context before accepting Phase 9.

No Phase 9 implementation is authorized by this planning deliverable alone beyond the user's existing project instructions for a later run. Optional remote workers, specialized/physical execution, stronger confinement, live providers and commercial outreach remain separately scoped. Completing the dashboard will not establish cross-industry discovery, novelty, real demand or full-project readiness; those remaining requirements still need explicit evidence and final audit.
