# Hackathon model qualification

**Offline integration verified. Live qualification blocked.** No inference ran during this repair and no new provider spend was incurred.

## Recovery and scope

- PR #2 worktree branch `chat/registered-experiments-20261103`, source HEAD `fcf343e8462e433f6187934bcc5cd4a62f228c65`. Started clean, four local commits ahead of the remote PR ref `eec42c4d1c97f928feefcae7424498223ecfbff4`. GitHub lists PRs #1 and #2 open. PR #1 is separate.
- Main is `85fedd8b854393096a77a065461fbb69eb1dd0bb`. Its pre-existing untracked `docs/PROJECT_STATUS_REPORT_.md` has SHA-256 `d530e081360309619ef62badb5006c8446a3b70525ca09f727f2bbec4b34b8ed`.
- Starting state saved before editing in `runtime/checkpoints/hackathon-qualification/source-baseline.json`. Staged reports, event anchors and request records remain in `runtime/staged-qualification-CLHJGg`. The earlier smoke evidence remains in `runtime/paid-validation-y7xYlF`. Provider and team changes are uncommitted in the existing branch.
- Source and experiment execution in the earlier staged qualification used `ec8ceff859ec9761ff8b6991fbfb9b02e87ab100`. `fcf343e` repaired the closed-root strict schema required list. This change preserves that repair.

## Provider findings

**Baseten.** The final staged critique requested `deepseek-ai/DeepSeek-V4.1-Flash-1017` and returned HTTP 403. The earlier smoke requested `zai-org/GLM-5.3-Flash` and also returned 403. The scripts used the generic Baseten credential environment. Both model IDs are outside the hackathon email's stated scope, which explains the denial if that restricted key backed the environment. The retained diagnostics do not establish that key binding, the provider's precise denial reason, or whether account/key status or formatting also mattered. Catalog visibility for a model did not establish inference permission. The new profile fixes `meta-models/muse-spark-open-1026` and restricts credential use to the exact inference endpoint. The public reasoning table for the general model does not establish that the restricted model accepts lower effort. The profile therefore omits reasoning configuration and native schema mode, with a prompt-delivered schema and strict local validation. [Baseten chat reference](https://docs.baseten.co/reference/inference-api/chat-completions), [Baseten reasoning](https://docs.baseten.co/inference/model-apis/reasoning).

**Meta.** The first proposal returned HTTP 400 on the schema later repaired in `fcf343e`. After the repair, the endpoint reached completion processing. The final staged proposal reported 1,207 input and 1,536 output tokens at its 1,536 cap and returned no usable proposal. The retained `INCOMPLETE_OR_REFUSED` code grouped length, other non-stop finishes and refusals. The raw finish reason, final message and reasoning-token breakdown were not retained. The cap and documented accounting support reasoning exhaustion and truncation as a plausible explanation. The exact split, finish reason and prompt contribution remain unknown. Direct Meta documents `max_completion_tokens` as a combined cap, hidden reasoning, and strict Chat Completions schema support for `muse-spark-1.3`. The adapter now records separate bounded failure codes and optional reasoning counts. Compact prompts and explicit `minimal` or `low` effort provide a smaller, documented probe configuration. [Meta reasoning](https://dev.meta.ai/docs/reasoning), [Meta chat schema](https://dev.meta.ai/docs/api-reference/chat-completions/schemas), [Meta structured output](https://dev.meta.ai/docs/structured-output).

| Role | Candidate | Credential evidence |
| --- | --- | --- |
| `RESEARCH_PROPOSALS` | Meta `muse-spark-1.3` | Prior paid smoke completed on the configured Meta credential. Source-grounded proposal remains unqualified. |
| `EXPLORATORY` | Meta `muse-spark-1.2` | Public model listing and staged configuration only. The earlier runs stopped before exploration. |
| `CRITIQUE` | Baseten `meta-models/muse-spark-open-1026` | The email establishes model scope for the restricted key. Exact-ID inference and final response capabilities remain unverified. |

The three roles can be configured as distinct identities. Only one has successful inference evidence. Qualification cannot substitute another key, model or alias.

## Financial blocker

Read-only SQLite joins matched reservation, settlement and provider failure events. Timestamps are UTC on 2026-11-03. Request keys end in `:0` and each provider failure event records attempt 1. The first two staged attempts reused the semantic fingerprint on different run IDs before and after the schema repair. They were separate dispatches. The final pair used new request identities and its critique used a fixed hypothesis. Replaying the retained staged requests added zero requests. No authoritative provider-side invoice or per-request usage export was available through a configured connector or browser session. Browser access was disabled in Work settings. No inference key was used for a billing or management lookup during this repair.

| Request | Start → ledger update | Run ID | Request key | Fingerprint | Usage evidence | Ledger state and USD |
| --- | --- | --- | --- | --- | --- | --- |
| Meta `muse-spark-1.3`, 400 | 17:54:52.921860 → 17:54:53.289952 | `761fef36-85ed-4d93-aa2a-c1435f6aaca5` | `staged-live-qualification-v1:RESEARCH_PROPOSALS:propose:0` | `c5a3ec906cc8493fbaae115216c1736fbe050c148d5bd3fccbac1f3fedaf8a5c` | None recorded | Uncertain $0.012416 |
| Meta `muse-spark-1.3`, after schema fix | 17:56:01.367223 → 17:56:06.741760 | `363016c2-2d12-4fed-9586-d3294c9c32ee` | `staged-live-qualification-v1:RESEARCH_PROPOSALS:propose:0` | `c5a3ec906cc8493fbaae115216c1736fbe050c148d5bd3fccbac1f3fedaf8a5c` | None recorded | Uncertain $0.012416 |
| Meta `muse-spark-1.3`, final cap | 17:56:29.044549 → 17:56:43.516695 | `7f23ffb4-cebd-4478-8d59-ca08ba1db266` | `RESEARCH_PROPOSALS:0` | `b7f5dbc9cc3427bac8252e9151fef3536d97714d452a4da611e668aee5cf52a4` | Adapter report 1,207 in and 1,536 out. $0.00803675 at uncached rates. Ledger usage empty. | Uncertain $0.016768 |
| Baseten `deepseek-ai/DeepSeek-V4.1-Flash-1017`, 403 | 17:56:43.530484 → 17:56:43.805493 | `7f23ffb4-cebd-4478-8d59-ca08ba1db266` | `CRITIQUE:0` | `0453c5a6428b3f1f9b552d7fa2e538e7bd2386f91564b99a027e5686bd549bdf` | None recorded | Uncertain $0.0036864 |
| Earlier Meta `muse-spark-1.3`, smoke success | 17:34:17.873933 → 17:34:21.819542 | `0fc33e76-adaa-4bda-8052-1436b65efbb5` | `paid-smoke-meta:0` | `f2cc9aedc1f6fcacc5afba5f541f55366f339f45b04db73db89084c66599475f` | Ledger 108 in and 350 out | Locally settled $0.0016225 |
| Earlier Baseten `zai-org/GLM-5.3-Flash`, 403 | 17:34:21.831319 → 17:34:22.199904 | `0fc33e76-adaa-4bda-8052-1436b65efbb5` | `paid-smoke-baseten:0` | `c4b9f80f41b371b778b9e97df9e3100b99c5f4d2c335c284e643bd1dbdfcbcf9` | None recorded | Uncertain $0.0011264 |

| Ledger scope | Settled USD | Open reserved USD | Uncertain USD | Conservative total USD | Remainder under $0.05 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Four staged attempts | 0 | 0 | 0.0452864 | 0.0452864 | 0.0047136 |
| Earlier smoke | 0.0016225 | 0 | 0.0011264 | 0.0027489 | |
| Combined conservative accounting | 0.0016225 | 0 | 0.0464128 | 0.0480353 | 0.0019647 |

The only settled record is the earlier Meta smoke, calculated locally from provider-reported tokens. Provider-side charges remain unconfirmed for every request. No reservations were released. At Meta's documented standard output rate, the existing 512-token cap alone costs up to $0.002176 before input. The restricted Baseten model's exact price and capabilities have not been established. A separately approved small live test is therefore **not ready**. Obtain an account-scoped usage export or invoice with matching times and IDs, preserve all unmatched holds, establish exact model scope and a conservative request cost within the original authorization, then seek explicit billable approval. [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits).

## Local acceptance

The final uncommitted source is identified by `runtime/hackathon-offline-dPxZrR/source-manifest.txt` (SHA-256 `66e61990b2518a9fb1d203faed7896396190fe59cd01a8fcb823ede18512efb2`). The corresponding working tree contains the provider contracts, adapters, router, team, proposal and catalog changes, two test-file updates, the example environment placeholder and the project records. The evidence directory contains per-command logs and exit codes. Earlier iterations found line-length and test typing issues, plus a Ruff requirement for Python 3.12 generic syntax. Those were corrected before the final run.

| Local check | Exit | Result |
| --- | ---: | --- |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run pyright` | 0 | 0 errors, warnings or information |
| Focused provider, team, budget, source, registered experiment and recovery suites | 0 | 106 passed, 0 failed |
| `uv run pytest -q` | 0 | 238 passed, 0 failed, 0 skipped. One existing Starlette TestClient deprecation warning. |
| `uv build --out-dir runtime/hackathon-offline-dPxZrR/dist` | 0 | Wheel and sdist built. The separate output path preserves earlier build evidence. |
| Three native CLI smokes and `git diff --check` | 0 | Encoding passed with three jobs. Dynamic allocation passed with six jobs. Greedy retained a failed candidate after one job. All smokes settled $0. |
| Retained source and experiment verification | 0 | Rehashed three search/DOI records and the versioned arXiv archive. Verified the publication, final staged model, recovery and fresh-run anchors at 9, 27, 41 and 35 events. |

The full mocked HTTP cycle used two configured Meta identities and one restricted Baseten identity over injected transports. Each typed proposal and critique cited its registered public-source fixture. Four fixture dispatches produced two candidate reviews and one content-addressed packet with digest `3a4f7923f8bf77a54c97ce2e54f98e7d207b2b04e216a9093e0e6fdf6e9852eb`. Reopening the store in cache-only mode returned the same digest with zero additional dispatches and zero additional evidence events. An unseen key failed before dispatch. The mock ledger settled $0.00064 in fixture rates with 400 input and 120 output tokens and no uncertain reservations. The sanitized packet and receipt are retained in the final evidence directory.

Focused cases cover the exact hackathon request, out-of-scope model and capability refusal, both documented reasoning settings, malformed and incomplete responses, duplicate JSON keys, HTTP and transport errors, uncertain usage, separate model identities, credentials, source ownership, withdrawal during review and replay, and persistent budget enforcement. Regular routing retains its bounded configured rate-limit retry policy. Qualification uses zero retries and one provider per role. Historical failed request keys remain fenced.

The staged allocation result remains 36/36 exact held-out optima with two replications and 25% minimum gain against a 15% threshold. Recovery reused two completed jobs and retried only the interrupted replica. Fresh results matched. The fixtures are synthetic, novelty is unknown, and commercial validation remains level 0. Production isolation, live full-team evidence, exact restricted endpoint capabilities and a provider billing reconciliation remain open. No live packet or overnight run was produced.

## Final stabilization and approval boundary

The earlier working-tree acceptance above is historical. Its 17 modified files and new report were reviewed as one qualification repair and committed as `43e1c631f8dd14df7c54767ce080a0c1c0da23c9`. The follow-up safety repair is `0b96c5da8024bce149add073cdb86839810e306b`. Both are on `chat/registered-experiments-20261103`. Main's untracked status report retained its recorded SHA-256. No provider request, deployment, push, or merge occurred during stabilization.

| Local verification | Result |
| --- | --- |
| Original repair, before its commit | Ruff and Pyright passed. The package built. 238 full-suite tests passed with one existing warning. |
| Stabilized code | Ruff and Pyright passed. 136 focused and 247 full-suite tests passed with no failures. Each pytest command reported the existing Starlette TestClient deprecation warning. |
| Distribution and CLI | Wheel and sdist built in a new directory. Encoding and dynamic allocation passed. Greedy retained a failed result. Each CLI run recorded zero provider spend. |
| Recovery and provenance | Revalidated seven retained event anchors covering smoke, the staged model attempts, publications, interrupted execution, and repeat execution. The rehearsal loaded the archived arXiv bytes and source metadata by digest. |
| Reproduction | Exact commands, source manifest, stderr/stdout, redacted scanner reports, read-only ledger, test artifacts and mock packet anchor are in `runtime/final-stabilization-9GtLk6`. The source/test/lock manifest digest is `3b246e72b783c096ca3f461731daf7ab888321a630f4b57642376082b0003e8e`. |

The new regressions initially reproduced six failures. Late overspend now records attributable usage without changing cancelled, paused, or other non-active run state. A timeout or ambiguous server outcome blocks further live fallback for that request while retaining the hold. An unexpected provider response model retains the full reservation and records observed tokens without settling at an unverified price. Non-finite Retry-After values use finite exponential backoff. Credential echo checks use the key actually sent, including JSON-escaped echoes when the environment changes during the request.

Two competing spawned processes sharing one SQLite database admitted one dispatch for a stable request. With distinct run IDs and two $0.03 estimates against a $0.05 daily cap, one process was denied before dispatch. Killing a process after mock dispatch left the open reservation intact, and a fresh coordinator refused to replay its key. Existing integration coverage verified cancellation during transport and backoff, snapshot and job recovery, malformed responses, source withdrawal, and the single-operator session boundary. The remaining runtime limits include single-root budget enforcement, mutable local storage requiring retained independent anchors, process-local provider concurrency, possible remote completion after local cancellation, and macOS confinement for reviewed workers. The loopback operator session is for a single trusted operator and does not establish tenant isolation. Shared-host or distributed service readiness remains open.

Credential review used Gitleaks v8.30.1 with 100% redaction across local Git refs/reflogs and tracked plus non-ignored worktree files. Review classified the historical hits as a synthetic credential-rejection fixture, two source-manifest digests and prose in a historical plan. Exact comparison against the two available configured credential values found zero matches in working files and local Git objects. The scan covers available local history and known credential values. Logs and committed artifacts contain no account credentials or invoice data from this task.

### Provider qualification matrix

| Identity | Documented or supplied | Locally simulated | Live evidence |
| --- | --- | --- | --- |
| Meta `muse-spark-1.3` | Standard pay-as-you-go, Chat Completions, 1,048,576-token vendor context, native JSON Schema and reasoning effort. The endpoint's completion cap includes reasoning. | `minimal` and `low` wiring, 512 combined output cap, typed source-grounded proposal, usage, refusal and truncation handling. | One historical small smoke succeeded. Staged research output failed. |
| Meta `muse-spark-1.2` | Standard pay-as-you-go, same chat contract and documented context. | `minimal` request, strict schema and typed exploratory proposal. | Account entitlement and research response remain unverified. |
| Baseten `meta-models/muse-spark-open-1026` | Supplied hackathon scope names the exact ID. Public Baseten chat docs establish the shared endpoint and `max_tokens` envelope. The public reasoning page covers a different ID and describes always-on reasoning. | Dedicated profile, explicit model ID, 512-token request, prompt schema, locally strict critique parsing and fail-closed response checks. | No inference on this exact ID. Entitlement, pricing, and whether the cap includes all billable generation require authoritative confirmation. |

[Meta models](https://dev.meta.ai/docs/models) · [Meta Chat Completions schema](https://dev.meta.ai/docs/api-reference/chat-completions/schemas) · [Meta reasoning](https://dev.meta.ai/docs/reasoning) · [Meta structured output](https://dev.meta.ai/docs/structured-output) · [Baseten Chat Completions](https://docs.baseten.co/reference/inference-api/chat-completions) · [Baseten reasoning](https://docs.baseten.co/inference/model-apis/reasoning)

### Ledger closure and account-owner actions

A read-only scan across 35 retained SQLite databases in both worktrees found the six non-mock inference reservations in the table above. Each had its matching reservation and settlement event. There were no orphan reservation events or additional non-mock inference rows in those databases. Separate historical scripts and receipts show catalog and management lookups outside the inference ledger. They do not prove billable inference or prove zero charges. Provider correlation IDs were not retained for the historical inference attempts, and an account-side export is necessary to determine completeness beyond the local records.

The combined ledger remains **$0.0016225 locally settled, $0 open reserved, $0.0464128 uncertain, $0.0480353 conservatively consumed and $0.0019647 available** under $0.05. The provider-confirmed total is **unknown**. Browser use was disabled in Work settings and no provider billing connector was available. Preserve the original rows and all unmatched holds.

1. A Meta team admin opens the correct Model API team, selects **Usage → Requests** and **Token usage**, then filters November 3, 2026 and `muse-spark-1.3`. Convert the dashboard's local time to UTC. Compare the four Meta entries at 17:34:17–17:34:22 and 17:54:52–17:56:44 UTC to the table. In **Billing → Payment activity**, download the applicable invoice or receipt. If aggregate usage is insufficient, the team admin can obtain a support confirmation for the matching windows, outcomes and gross billed amounts. [Meta usage](https://dev.meta.ai/help/usage-and-limits/api-usage) · [Meta billing](https://dev.meta.ai/help/billing/unrecognized-payment) · [Meta support](https://dev.meta.ai/help/support/contact-support)
2. A Baseten workspace owner opens **Workspace settings → Billing**, then inspects November 3 Model APIs usage for DeepSeek V4.1 Flash and GLM-5.3-Flash at the two table timestamps. An already authorized management credential can read `GET https://api.baseten.co/v1/billing/model_apis` for the daily subtotal or `GET /v1/billing/usage_summary` for the per-model breakdown. The restricted inference key stays out of management requests. For ambiguous or shared totals, obtain a provider confirmation for the two 403s and the restricted SKU's exact entitlement, input and output rates, minimum charges, and how its cap treats reasoning. [Baseten Model API costs](https://www.baseten.co/resources/changelog/model-api-costs/) · [Baseten usage breakdown](https://www.baseten.co/resources/changelog/retrieve-billing-usage-via-api/)
3. Retain only sanitized account evidence. Match by provider, account, model, UTC window, outcome and request ID where available. Keep aggregate entries unresolved if other traffic could explain them. Record the matching gross rated charges separately from credits and payments. Recompute conservative headroom, preserving unmatched holds, before requesting explicit approval.

### Minimal proposed live protocol — BLOCKED

The smallest complete existing ResearchTeam path is four sequential calls. It produces two theoretical proposals through different Meta identities and routes both critiques through the distinct restricted Baseten identity. Use a single archived, hash-verified public source, the versioned arXiv record `2405.13450v1`. Reattach its exact archived source record and verify its content address. Use topic `When does exact optimization improve 0–1 knapsack allocation?`, domain `operations research` and key `qualification-v1`. Retain the run ID, source ID, route settings and keys for deterministic replay.

| Inference slot | Model | Output cap | Local context admission |
| --- | --- | ---: | ---: |
| Proposal | Meta `muse-spark-1.3`, `minimal`, strict schema | 512 | 4,096 |
| Independent critique | Baseten `meta-models/muse-spark-open-1026`, prompt schema | 512 | 4,608 |
| Exploratory proposal | Meta `muse-spark-1.2`, `minimal`, strict schema | 512 | 4,096 |
| Independent critique | Baseten `meta-models/muse-spark-open-1026`, prompt schema | 512 | 4,608 |

The local admission values are deliberately small software bounds. The rehearsal observed 4,006 units for each proposal and 4,309 for each critique under the adapter's byte-plus-framing guard. A 4,096-unit Baseten attempt failed before dispatching its critique in the mock rehearsal. The 4,608-unit setting passed with the same typed fixture. A longer live proposal may make the subsequent critique exceed that guard. In that case stop without widening it. The 512-token cap is the existing full-team cap and includes the response JSON. The plan uses documented minimal reasoning effort on Meta and keeps the cap below the earlier 1,536-token request. Its adequacy on the real endpoints is unverified.

Use one owner-only runtime, a single foreground operator, one route per role, zero retries and fallback, 25 seconds per call and a 120-second outer cancellation deadline. Before any authorized dispatch, freeze the complete plan and confirm the full four-call estimate against the combined budget. Set the run and daily caps to no more than the reconciled authorization and verify each estimate also fits the router's per-request allocation. Avoid other paid work across runtime roots. Stop on the first ambiguous, malformed, invalid, cancelled or over-budget result. Preserve the receipt or reservation, and require reconciliation before any further attempt. The process-death recovery scenario was tested with mocks and does not warrant deliberately interrupting live inference.

If all four calls succeed, validate the proposal and critique citations, verify the typed packet and its content address, and retain the evidence chain and usage records. Restart with `Router(..., cache_only=True)`, the original inputs and the same stable keys. Require the same packet digest, the same event count and no new transport calls or reservations. The local rehearsal produced digest `9e9d2089901bbf502f3a30160b8bd1a55683a027b334aba3f27b22545e022e46` and a 15-event anchor with zero replay dispatches and zero replay events. It used a fixture Baseten rate and made no network inference.

At the documented Meta Standard uncached rates of $1.25 per million input tokens and $4.25 per million completion tokens, the two Meta slots require **$0.014592** combined using the adapter's full configured input allowance and both completion caps. That includes reasoning and assumes no cache discount or retry. The known Meta component alone would take the combined conservative total to **$0.0626273**. The two Baseten slots would add twice the rounded-up cost of 4,608 input tokens, 512 completion tokens including any billable reasoning, and any fixed charge. A defensible full maximum cannot be stated until Baseten confirms those exact rates and billing semantics. Treat the full bound as unknown and already over budget on the Meta component. [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits)

| Gate | Decision |
| --- | --- |
| Offline verification and review | **GO** on the committed local branch. |
| Live testing | **NO-GO.** The known reservation exceeds available headroom, provider confirmation and entitlements are incomplete, and spending approval remains separate. |
| Overnight operation | **NO-GO.** Live qualification, production isolation and bounded long-duration acceptance remain open. |
| PR #2 merge | **NO-GO.** The remote PR does not contain the local verified commits. Human review of the exact revision and a scoped acceptance decision remain open. |
