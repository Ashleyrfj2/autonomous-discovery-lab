# Security model

Trust boundaries: user configuration vs untrusted retrieved text/model proposals; orchestrator vs fixed reviewed worker; database vs filesystem artifacts; local tests vs live providers; external market records vs synthetic claims. Protect secrets, host files, network, spend, evidence and availability.

Only allowlisted experiment IDs and typed numeric parameters reach a worker. Never execute generated code, command text, arbitrary paths, deserialized pickle or plugins. Worker cwd is temporary, environment minimal, stdin bounded JSON. Enforce wall/CPU/memory/output caps, fail closed on unavailable controls. Process limits do not protect against malicious trusted source; arbitrary-code execution is unsupported. Do not describe the subprocess as a general sandbox.

Retrieved documents cannot set instructions or permissions. Fetching requires policy authorization, HTTP(S) validation, blocked private/link-local/reserved targets, bounded body/time and redirect revalidation; no local file URL. API auth headers never enter persisted errors. Validate outputs and sanitize logs centrally. Environment files excluded from Git; examples contain placeholders. Provider failure retains state, reservations cap unknown consumption conservatively, and retries never silently duplicate expensive requests.

SQLite transactions, lease fencing, idempotency and atomic checkpoints protect recovery. Hash chaining and external anchor exports detect tampering relative to retained trusted roots, not absolute immutability. Commercial gates require independently inspectable external evidence; model declarations cannot count. Local software budgets are not provider-enforced hard spend caps. No deployments, merges or billable workloads are currently authorized.
