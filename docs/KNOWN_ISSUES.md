# Known issues

- Phases 0–3 locally verified; phases 4–9 remain, including external retrieval, branching, commercial evidence and extended scheduling.
- Execution supports only reviewed encoding-v1 algorithms. Other ideas need additional reviewed implementations or an authorized stronger execution backend. The cross-industry mission remains intact; the encoding demo is a first experiment family.
- Local macOS confinement uses deprecated/private Seatbelt profiles. Native denial was tested on this host. Unsupported platforms fail closed. This is not a production arbitrary-code sandbox.
- Darwin rejects address/data rlimits on this host. Parent RSS polling enforces the configured memory limit and may observe brief overshoot between samples; bounded allowlisted inputs also constrain allocation. CPU, wall, output, file-size and file-descriptor bounds are separate.
- No live Meta/Baseten calls, pricing/model capability acceptance, deployment, remote workers, production readiness or hackathon eligibility verification.
- Completed pure computational stages are not repeated on recovery; interruption during unfinished execution can require recomputation. Phase 8 must reconcile durable sub-jobs and cancellation during work.
