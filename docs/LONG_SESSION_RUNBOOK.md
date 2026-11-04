# Long-session runbook

Use branch `integration/ai-native-discovery` and the capability-v1 profiles below. These are the current AI-native milestone profiles. The older `session-qualification.json`, `session-four-hour.json`, `discovery-meta.json` and their historical estimates remain available for saved v2 sessions; do not substitute manifests when resuming any registered run.

**Preserve the first live qualification. Never resume or rerun `session-4374c2fa7c8f44708fef506893831998` in `runtime/controlled-live`.** Its zero-hypothesis packet is a regression baseline. New qualification and supervised runs each need a fresh root. No paid inference or 90-minute live run was executed by the repair task.

## Configuration, reasoning and usage

The current mission explicitly investigates gaps AI could newly make possible, with configurable `ai_native` and `open_science` tracks. Edit a copy of the profile before registration to select only one track or a new objective. Every planned direction records its selection/change reason. The default has no favored industry. Read the [method and twelve repair sentinels](research_quality/CAPABILITY_V1.md).

| Inference stage | Model | Reasoning | Completion cap including reasoning | Caller timeout |
| --- | --- | --- | ---: | ---: |
| Research planning | Spark 1.3 | medium | 4,096 | 30 s |
| Atomic extraction / relevance | Spark 1.3 | low | 4,096 | 20 s |
| Gap / constraint identification | Spark 1.2 | medium | 4,096 | 30 s |
| AI suitability, mechanistic bridge and hypothesis | Spark 1.2 | high | 8,192 | 45 s |
| Independent adversarial critique | Wonder 1.0 | high | 8,192 | 45 s |

Retrieval admission, recovery routing and final report synthesis are deterministic local code and make no extra inference request. High reasoning is an experimental allocation, not an established optimum. Both 4,096 and 8,192 caps passed strict simulated HTTP contracts. Real high-reasoning output sufficiency, quality, latency and prices charged remain qualification measurements. Official support/rates: [Meta reasoning](https://dev.meta.ai/docs/reasoning), [models](https://dev.meta.ai/docs/models), [chat parameters](https://dev.meta.ai/docs/protocols/chat-completions), [pricing](https://dev.meta.ai/docs/pricing-rate-limits). Read-only catalog checks passed for all three model IDs during local acceptance.

The provider manifest keeps three distinct model identities. Request-local overrides avoid changing other routes globally. Each adapter's 45-second upper timeout remains bounded by the branch deadline. A caller timeout is an ambiguous dispatch; the reservation stays unresolved and the controller refuses automatic retry/resume. A background transport may still finish and incur usage. Stage checkpoints renew the existing short fenced lease.

| Current profile | Wall-time upper bound | Branches | Attempts | Conservative total tokens | Gross standard-rate upper estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `session-capability-qualification.json` | 1,500 s | 2 | 26 | 1,403,648 | $3.787648 |
| `session-capability-ninety-minute.json` | 5,400 s | 24 | 312 | 16,843,776 | $45.451776 |

Each branch has 600 seconds, at most 13 model calls, seven searches (source/target/prior art for two directions plus one targeted recovery), and fourteen bibliographic fetches. Each role reserves 48,000 input tokens per attempt conservatively, plus its configured completion cap. Worst serial stage time is 450 seconds, with up to 112 seconds of indexed fetch timeout before local overhead and optional registered seeds. Deadline and cancellation can still interrupt a branch. Whole-branch admission is 701,824 tokens / $1.893824; no retries and one concurrent branch. These profile envelopes replace the historical $1.45552 qualification estimate. Duration, errors, stagnation and actual branch timing may stop far earlier than the count maxima. No per-call/run/day/qualification dollar caps are reinstated. An optional aggregate ceiling remains null. Credits/caching discounts are excluded; provider-confirmed billing is separate.

Paused time counts against the 1,500-second qualification deadline. Review and resume promptly. An expired qualification remains preserved; investigate before separately authorizing another fresh run. Do not alter its registered limits or automatically repeat settled calls.

## 1. Enter the project and select the existing credential file

The commands expose the existing file's path only. Never print, copy into Git, or pass the key value as an argument.

```sh
cd /Users/ashley/Documents/Codex/2026-11-04/codex-autonomous-discovery-lab-integrate-research/long-session
ADL_ENV=/Users/ashley/Code/autonomous-discovery-lab/.env
PROVIDERS=config/discovery-capability-meta.json
QUAL_PROFILE=config/session-capability-qualification.json
LONG_PROFILE=config/session-capability-ninety-minute.json
uv sync --locked
```

If `META_API_KEY` is already exported, `--env-file "$ADL_ENV"` can be omitted. Configuration paths contain no secret values. All live commands require explicit authorization flags; their presence is the operator's spending authorization.

## 2. Preflight (no inference)

```sh
uv run autodiscover session preflight --profile "$QUAL_PROFILE" --providers "$PROVIDERS"
uv run --env-file "$ADL_ENV" autodiscover session preflight \
  --profile "$QUAL_PROFILE" --providers "$PROVIDERS" --check-model-access --allow-network
```

The second command performs authenticated catalog GET requests only. It does not test reasoning or inference.

## 3. Non-billable dry run and resume

```sh
DRY_ROOT=$(mktemp -d)
uv run autodiscover --root "$DRY_ROOT" session dry-run \
  --profile "$QUAL_PROFILE" --providers "$PROVIDERS" > "$DRY_ROOT/start.json"
DRY_ID=$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$DRY_ROOT/start.json")
uv run autodiscover --root "$DRY_ROOT" session status "$DRY_ID"
uv run autodiscover --root "$DRY_ROOT" session resume "$DRY_ID" --providers "$PROVIDERS"
uv run autodiscover --root "$DRY_ROOT" session report "$DRY_ID" > "$DRY_ROOT/report.json"
```

This uses authored synthetic sources and scripted models, costs zero and makes no network calls. It exercises the shared controller and capability contracts. It is not scientific, live-model or commercial evidence.

## 4. Start a NEW controlled Meta qualification (billable; operator action)

`mktemp` guarantees a fresh root. Preserve the printed root and session ID; use `resume`, never another `start`, for continuation of this session.

```sh
QUAL_ROOT=$(mktemp -d "$PWD/runtime/controlled-capability-XXXXXX")
printf '%s\n' "$QUAL_ROOT"
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session start \
  --profile "$QUAL_PROFILE" --providers "$PROVIDERS" --authorize-live --allow-network
```

After the first completed branch, expect `PAUSED` / `QUALIFICATION_CHECKPOINT`, unless an earlier safety boundary applies. Copy the printed session ID:

```sh
QUAL_ID=session-PASTE_THE_NEW_ID
uv run autodiscover --root "$QUAL_ROOT" session status "$QUAL_ID"
uv run autodiscover --root "$QUAL_ROOT" session report "$QUAL_ID" > "$QUAL_ROOT/checkpoint-report.json"
```

Inspect `usage`, unresolved reservations, direction notes, search stages and `dossiers[].packet`. Each packet contains stage settings, role/model identities, sources, findings, opportunity assessments, original/revised hypotheses, critiques and rejection reasons. For a concise local inspection:

```sh
uv run python - "$QUAL_ROOT/checkpoint-report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print(json.dumps({k: r[k] for k in ['status', 'stop_reason', 'usage', 'unresolved_reservations']}, indent=2))
for d in r['dossiers']:
    p = d['packet']
    print(json.dumps({'child_id': p['run_id'], 'routes': p['routes'],
                     'stages': p['specification']['capability']['stages'],
                     'hypotheses': p['candidates'], 'closed': p['quality_closed_directions']}, indent=2))
PY
```

An operational pass requires genuine Meta identities and inference, real substantive source/target coverage, recorded prior-art search (limitations allowed), at least one substantive valid independent critique, provisional labels, settled locally attributable requests, no unresolved reservations, correct direction associations, pause/resume and exact replay. A zero-hypothesis result can be scientifically appropriate, but does not complete the operational critique gate. Diagnose before deciding whether a separately authorized bounded question is warranted. Do not weaken the gates or auto-run another qualification.

## 5. Resume and final qualification report

```sh
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session resume "$QUAL_ID" \
  --providers "$PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$QUAL_ROOT" session report "$QUAL_ID" > "$QUAL_ROOT/final-report.json"
CHILD_ID=$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1]))["dossiers"][0]["packet"]["run_id"])' "$QUAL_ROOT/final-report.json")
uv run autodiscover --root "$QUAL_ROOT" discover --cache-only --run-id "$CHILD_ID"
```

Replay must preserve packet digest, request totals and evidence anchor with zero external calls. Compare local accounting against the provider ledger. Provider billing reconciliation and human semantic review remain external acceptance evidence. Any uncertain dispatch, incomplete critique, source integrity failure, manifest mismatch or unexplained charge leaves qualification pending/NO-GO.

## 6. Supervised 90-minute launch only after qualification passes

Use an attended Mac with power/network. `caffeinate -i` keeps the foreground process awake. No 90-minute run was launched during implementation.

```sh
uv run autodiscover session preflight --profile "$LONG_PROFILE" --providers "$PROVIDERS"
LONG_ROOT=$(mktemp -d "$PWD/runtime/discovery-capability-ninety-minute-XXXXXX")
printf '%s\n' "$LONG_ROOT"
caffeinate -i uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session start \
  --profile "$LONG_PROFILE" --providers "$PROVIDERS" --authorize-live --allow-network
```

Copy the printed session ID into a second terminal with the same directory, environment-file path, manifest and root variables:

```sh
LONG_ID=session-PASTE_THE_NEW_ID
uv run autodiscover --root "$LONG_ROOT" session status "$LONG_ID"
uv run autodiscover --root "$LONG_ROOT" session report "$LONG_ID" > "$LONG_ROOT/report.json"
uv run autodiscover --root "$LONG_ROOT" session pause "$LONG_ID"
uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session resume "$LONG_ID" \
  --providers "$PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$LONG_ROOT" session cancel "$LONG_ID" --confirm
```

Pause closes admission and drains to a checkpoint; wait for PAUSED before resuming. SIGINT/SIGTERM use the same cooperative boundary. Cancel immediately fences the session and cannot be resumed. An already dispatched request can still finish and be billed. Five consecutive branches without reviewed knowledge, a distinct provisional candidate or a useful reviewed critique/negative result stop exploration; unrelated new papers cannot reset this counter. Direction changes and stop reasons remain auditable in packets and branch outcomes. The 90-minute duration is a maximum, never a requirement to keep spending without progress.

## Evidence and failure recovery

SQLite `lab.sqlite3` plus WAL is authoritative; keep sidecars with an inactive root. `artifacts/` contains hashed captures/checkpoints/packets. Never edit reservations or their request identities to force continuation. `session report` and cache-only replay use read-only snapshots. After process death, inspect `status`, preserve the root and use the original ID/manifest for `resume`. Settled cached responses survive a crash before the next checkpoint. A changed stage policy or provider manifest cannot reuse the settled identity.

`REQUEST_RECONCILIATION_REQUIRED` means preserve the listed IDs/model/time and reconcile with the provider. Resume refuses unresolved RESERVED/UNCERTAIN requests; no automatic adjudication command is provided. Local mock recovery and virtual 90-minute evidence do not qualify fully unattended overnight operation. That remains NO-GO pending supervised live behavior, charge reconciliation and an operator reconciliation procedure. PR #2 remains draft and unmerged.
