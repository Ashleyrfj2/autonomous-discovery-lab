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
