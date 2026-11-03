# Known issues

- Local phase gates 0–7 have passed. Phases 8–9 remain: extended scheduling and monitoring/approval interfaces. See PROJECT_STATUS_REPORT.md for the current scope and limitations.
- Execution supports only reviewed encoding-v1 algorithms. Broad quantitative research proposals can be retained as theoretical; executing them needs additional reviewed implementations or an authorized stronger execution backend. The cross-industry mission remains intact; the encoding demo is a first experiment family.
- Local macOS confinement uses deprecated/private Seatbelt profiles. Native denial was tested on this host. Unsupported platforms fail closed. This is not a production arbitrary-code sandbox.
- Darwin rejects address/data rlimits on this host. Parent RSS polling enforces the configured memory limit and may observe brief overshoot between samples; bounded allowlisted inputs also constrain allocation. CPU, wall, output, file-size and file-descriptor bounds are separate.
- No live Meta/Baseten calls, actual buyer/pilot/payment validation, pricing/model capability acceptance, deployment, remote workers, production readiness or hackathon eligibility verification. Positive commercial classifications in tests are source-bound operator-review contract fixtures, not real market evidence.
- Completed pure computational stages are not repeated on recovery; interruption during unfinished execution can require recomputation. Phase 8 must reconcile durable sub-jobs and cancellation during work.
