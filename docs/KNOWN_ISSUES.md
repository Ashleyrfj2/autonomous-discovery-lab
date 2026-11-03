# Known issues

- Local phase gates 0–8 have passed. Phase 9 monitoring/approval interfaces remain unimplemented. See PROJECT_STATUS_REPORT.md for the current scope and limitations.
- Execution supports only reviewed encoding-v1 algorithms. Broad quantitative research proposals can be retained as theoretical; executing them needs additional reviewed implementations or an authorized stronger execution backend. The cross-industry mission remains intact; the encoding demo is a first experiment family.
- Local macOS confinement uses deprecated/private Seatbelt profiles. Native denial was tested on this host. Unsupported platforms fail closed. This is not a production arbitrary-code sandbox.
- Darwin rejects address/data rlimits on this host. Parent RSS polling enforces the configured memory limit and may observe brief overshoot between samples; bounded allowlisted inputs also constrain allocation. CPU, wall, output, file-size and file-descriptor bounds are separate.
- No live Meta/Baseten calls, actual buyer/pilot/payment validation, pricing/model capability acceptance, deployment, remote workers, production readiness or hackathon eligibility verification. Positive commercial classifications in tests are source-bound operator-review contract fixtures, not real market evidence.
- Phase 8 preserves committed sub-jobs and completed replications; unfinished pure computation can be explicitly retried within persisted bounds. Unknown external inference outcomes retain reservations and require reconciliation; local cancellation cannot prove server cancellation or zero billing.

- Phase 8 accepted evidence is a short 3.76-second mock-provider operation, not a long-duration soak. Transport daemon threads (at most eight per process) may outlive a caller deadline. Local OS permissions/signals and SQLite writer waits can extend graceful cleanup; no hard kernel/provider return-time guarantee. Legacy runs without topic/release anchors retain explicit audit limitations.
