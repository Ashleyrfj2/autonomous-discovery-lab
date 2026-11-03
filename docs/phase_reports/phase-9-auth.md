PHASE: 9 / P9-AUTH
STATUS: LOCALLY_VERIFIED task; full phase IN_PROGRESS

IMPLEMENTED: FastAPI loopback-only authenticated read endpoints backed by P9-READ; foreground serve CLI requires TTY and a temporary12–200-character operator passphrase, never printed or persisted. Scrypt verification; rotating single-operator HttpOnly SameSite=Strict session cookie, eight-hour expiry and logout; strict peer/Host/Origin/fetch-site checks, CSRF for mutations, same-origin JSON login, bounded bodies/read duration/responses, no-store/CSP/nosniff headers, disabled public API docs/access logs. Unknown exceptions and validation/source bodies are not echoed/logged. No workers, approvals or budget mutations exposed.

VERIFIED: Ruff passes; Pyright0 findings;163 full tests passed in13.42s; wheel/sdist built. Thirteen operator tests cover authentication, cookie rotation, logout/expiry, CSRF, rebinding/cross-origin/remote-peer denial, forged forwarded headers, request limits/schema/rate failures, read pagination/state preservation, integrity rejection, duplicate headers, exception secrecy, TTY-only startup and real loopback HTTP login/read/bounded shutdown.

EVIDENCE: phase-9-auth/{tests.xml,verification.json,source-manifest.json}.
WARNING: One upstream Starlette TestClient httpx deprecation warning is retained and unsuppressed; tests, including actual HTTP, pass.
DECISION: DEC-017
LIMITS: API is local single-operator and read-only apart from session login/logout. Dashboard, workflow controls, market review UI and browser qualification remain. Sessions rely on local operator passphrase trust; no production/multi-user/remote exposure claim. HTTP on loopback is intentional; no external deployment.
NEXT: Implement transactional versioned/idempotent operator controls; dashboard design awaits an explicit paid12ui spending limit.
