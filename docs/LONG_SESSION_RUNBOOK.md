# Long-session runbook

Use branch `integration/ai-native-discovery`. The current repaired short qualification uses `session-capability-qualification-evidence-v3.json` / `discovery-capability-evidence-v3.json`, the opt-in capability-v2 evidence-role protocol, and the unchanged `discovery-capability-meta-medium-v2.json` provider manifest. Existing profiles remain frozen for historical registrations; the next milestone is the controlled Meta test, not the 90-minute session. The older `session-qualification.json`, `session-four-hour.json`, `discovery-meta.json` and their historical estimates remain available for saved v2 sessions; do not substitute manifests when resuming any registered run.

**Preserve the first live qualification. Never resume or rerun `session-4374c2fa7c8f44708fef506893831998` in `runtime/controlled-live`.** Its zero-hypothesis packet is a regression baseline. **Also never resume `session-4c376b05f4e8440aab2d15c30a603ec8` in `runtime/controlled-capability-wRPtYg`.** Its first planning request timed out and remains UNCERTAIN with a $0.077408 local hold, no reported usage, and unknown provider billing/processing. Preserve both historical qualifications. New qualification and supervised runs each need a fresh root. This repair made no paid calls or live launches.

**Preserve the saved medium qualification too:** `session-af4a91eb5bc64536b220acfde11a00d5` in `runtime/controlled-capability-medium-v2-r6kNh7`. It reached the first checkpoint with six settled requests / $0.093511 locally calculated, one rejected proposal and zero critiques. It has no unresolved requests, but it did not pass the critique gate; provider billing remains unconfirmed. Never rewrite its packet or resume it to try the new contracts. The older $0.077408 uncertain request remains unresolved and separate. All three historical live roots are regression evidence.

The evidence-v3 profile implements the [evidence-role repair](phase_reports/EVIDENCE_ROLES_REPAIR_2026-11-04.md). Relevant source-bound context can inform gap/target-need analysis without proving causality or efficacy. Need, mechanism, observed constraint and measured improvement have separate roles; empirical claims must bind matching supporting findings. An observed constraint needs explicit source/role/domain support, a registered claim and independent assessment. Placeholders, structural contradictions and non-units fail closed. Provisional hypotheses still require a defensible mechanism, independent target context, meaningful measurement and critique; measured superiority is not required or conferred. Labels and matching quotations are not a general semantic-entailment proof.

## Configuration, reasoning and usage

The current mission explicitly investigates gaps AI could newly make possible, with configurable `ai_native` and `open_science` tracks. Edit a copy of the profile before registration to select only one track or a new objective. Every planned direction records its selection/change reason. The default has no favored industry. Read the [method and twelve repair sentinels](research_quality/CAPABILITY_V1.md).

| Inference stage | Model | Reasoning | Completion cap including reasoning | Caller timeout |
| --- | --- | --- | ---: | ---: |
| Research planning | Spark 1.3 | low | 4,096 | 90 s |
| Atomic extraction / relevance | Spark 1.3 | low | 4,096 | 45 s |
| Gap / constraint identification | Spark 1.2 | medium | 4,096 | 60 s |
| AI suitability and mechanistic analysis (shared proposal call) | Spark 1.2 | medium | 8,192 | 90 s |
| Hypothesis generation (same proposal call, no extra request) | Spark 1.2 | medium | 8,192 | 90 s |
| Independent adversarial critique | Wonder 1.0 | medium | 8,192 | 90 s |

Retrieval admission, recovery routing and final report synthesis are deterministic local code and make no extra inference request. Medium is a candidate allocation, not demonstrated superior reasoning. Completion caps remain unchanged because the observed failure was timeout, not output exhaustion. Caps and billing include hidden reasoning; never add reasoning tokens to completion tokens a second time. Official [reasoning](https://dev.meta.ai/docs/reasoning) and [pricing](https://dev.meta.ai/docs/pricing-rate-limits) were rechecked for this repair; Spark input/output $1.25/$4.25 per million and Wonder $4/$20. No inference was made to verify latency, token sufficiency or charged prices.

Use `discovery-capability-evidence-v3.json`, `session-capability-qualification-evidence-v3.json` and `discovery-capability-meta-medium-v2.json` together. The earlier medium-v2 discovery/session profiles remain frozen and select capability-v1; do not edit or resume their saved qualification. New profiles change evidence contracts and prompt identity, not stage reasoning or timeout bounds. The embedded discovery spec matches the standalone file exactly. Provider reasoning defaults are unchanged; actual stages override them. Each provider manifest bound is 90s, within the adapter/request 120s maximum. Actual caller AND httpx connect/read/write/pool bounds are the stage values above. HTTP operation bounds do not guarantee server cancellation: a background transport can outlive cancellation and be billed. Keep holds, classify ambiguity and never automatically retry it. Stage checkpoints renew the existing 300s fenced lease.

| Profile | Wall-time maximum | Branches | Attempts | Conservative tokens | Gross standard-rate estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| NEW `session-capability-qualification-evidence-v3.json` | 3,000 s | 2 | 26 | 1,403,648 | $3.787648 |
| Historical `session-capability-qualification.json` (do not reuse for new qualification) | 1,500 s | 2 | 26 | 1,403,648 | $3.787648 |
| Existing `session-capability-ninety-minute.json` (separately gated; unchanged settings) | 5,400 s | 24 | 312 | 16,843,776 | $45.451776 |

A NEW qualification branch has 1,200s, at most 13 model calls, seven searches and fourteen bibliographic fetches. Worst serial model wait is 90 + 3×45 + 3×60 + 3×90 + 3×90 = 945s, plus fourteen 8s index-fetch bounds = 1,057s, leaving 143s for local work. There are no registered seed documents in this profile. Branch/session cancellation can stop earlier. Two full branch budgets plus 600s review/overhead fit 3,000s; paused time counts. Resume promptly and only from a valid checkpoint. Duration is a bound, not a promise to use every call.

Per branch input maximum: 13×48,000 = 624,000. Inclusive completion maximum: 4,096 + 3×4,096 + 3×4,096 + 3×8,192 + 3×8,192 = 77,824. Total 701,824 tokens / $1.893824 per branch; twice for qualification. Spark accounts for 480,000 input + 53,248 completion; Wonder 144,000 + 24,576. No retries, one concurrent branch, no provider-managed web tools or paid search. Credits/cache discounts excluded. Cost estimate is unchanged despite the reasoning reduction because the hard token envelope is unchanged. No per-call/run/day/qualification dollar cap is restored; optional aggregate ceiling stays null. The prior $0.077408 uncertain hold and first session's $0.012262 locally calculated settled usage are separate historical liabilities, not part of the new estimate or proof of provider billing.

## 0. Investigate the previous uncertain request before any paid test

Do not resume, reconcile by editing, or modify the old root. Preserve the complete inactive root including SQLite WAL/SHM, checkpoints, logs and artifacts. Work on a copy for additional inspection:

```sh
cd /Users/ashley/Documents/Codex/2026-11-04/codex-autonomous-discovery-lab-integrate-research/long-session
OLD_REVIEW=$(mktemp -d "$PWD/runtime/timeout-review-XXXXXX")
cp -R runtime/controlled-capability-wRPtYg/. "$OLD_REVIEW/"
uv run autodiscover --root "$OLD_REVIEW" session report \
  session-4c376b05f4e8440aab2d15c30a603ec8 > "$OLD_REVIEW/report.json"
uv run python - "$OLD_REVIEW" <<'PYREVIEW'
import json, sys
from pathlib import Path
from autodiscover.orchestrator.store import SnapshotStore
child = 'discovery-3c2fc77f741841abc9099e464276c8443abedc5e19abdbbc60a764e0b3cad4ad'
with SnapshotStore(Path(sys.argv[1])) as store:
    with store.connection() as db:
        rows = db.execute("SELECT kind,timestamp,payload_json FROM events WHERE run_id=? AND kind IN ('cost_reserved','cost_settled','provider_failed') ORDER BY seq", (child,))
        for row in rows:
            print(json.dumps(dict(row)))
PYREVIEW
```

Use the account owner's authenticated Meta billing/usage and request records, matching account/project, UTC dispatch window **2026-11-04 22:03:37.046–22:04:07.061 UTC** (allow for later remote completion), model `muse-spark-1.3`, planning request, 4,096 completion bound and endpoint `/v1/chat/completions`. Local reservation `a0bca7a6-91a3-4b90-9e63-91b3b4afaa75`, key `discovery-v2:plan:0`, is a local correlation ID, not a provider request ID. No provider response/request ID was retained for the timeout. If dashboard records cannot identify it, ask provider support to trace the exact window/account/model; do not send credentials or private prompt contents. Preserve sanitized exports or support findings with capture time and source. Explicit processing/completion, token/reasoning usage, and actual charge/no-charge evidence are distinct facts. A zero response count, absent immediate dashboard line or zero local tokens is insufficient.

No account records were available in this repair; outcome remains **UNRESOLVED**. If investigation cannot confirm it, retain the hold and this uncertainty, and document that finding before separately authorizing a new root. Even provider-confirmed outcome does not authorize changing the preserved historical reservation in this task. The new qualification can measure its own outcome; it cannot retroactively reconcile the old request.

## 1. Enter the project and select the existing credential file

The commands expose the existing file's path only. Never print, copy into Git, or pass the key value as an argument.

```sh
cd /Users/ashley/Documents/Codex/2026-11-04/codex-autonomous-discovery-lab-integrate-research/long-session
ADL_ENV=/Users/ashley/Code/autonomous-discovery-lab/.env
PROVIDERS=config/discovery-capability-meta-medium-v2.json
LONG_PROVIDERS=config/discovery-capability-meta.json
QUAL_PROFILE=config/session-capability-qualification-evidence-v3.json
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

This uses authored synthetic sources and scripted models, costs zero and makes no network calls. CLI dry-run shortens the duration to 90 seconds; it preserves stage settings and does not demonstrate 3,000 seconds of wall-time stability. It exercises the shared controller and capability contracts. It is not scientific, live-model or commercial evidence.

## 4. Start a NEW controlled Meta qualification (billable; operator action)

`mktemp` guarantees a fresh root. Preserve the printed root and session ID; use `resume`, never another `start`, for continuation of this session.

```sh
QUAL_ROOT=$(mktemp -d "$PWD/runtime/controlled-capability-evidence-v3-XXXXXX")
printf '%s\n' "$QUAL_ROOT"
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session start \
  --profile "$QUAL_PROFILE" --providers "$PROVIDERS" --authorize-live --allow-network
```

These commands are for a separately authorized future operator action; do not run during the repair. Save the printed root and ID in your operator notes. After the first completed branch, expect `PAUSED` / `QUALIFICATION_CHECKPOINT`, unless an earlier safety boundary applies. Copy the printed session ID:

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

Review per-request reasoning-token usage and uncertain holds through a read-only snapshot (inclusive completion usage already includes reasoning):

```sh
uv run python - "$QUAL_ROOT" <<'PYUSAGE'
import json, sys
from pathlib import Path
from autodiscover.orchestrator.store import SnapshotStore
with SnapshotStore(Path(sys.argv[1])) as store:
    with store.connection() as db:
        rows = db.execute("SELECT id,run_id,request_key,provider,model,status,reserved_nano,charged_nano,usage_json FROM reservations ORDER BY rowid")
        for row in rows:
            record = dict(row)
            usage = json.loads(record.pop('usage_json') or '{}')
            record['usage'] = usage
            record['visible_completion_tokens_if_reported'] = (
                usage['output_tokens'] - usage['reasoning_tokens']
                if usage.get('reasoning_tokens') is not None else None
            )
            record['needs_reconciliation'] = record['status'] in {'RESERVED','UNCERTAIN'}
            print(json.dumps(record))
PYUSAGE
```

`reasoning_tokens` absent means unreported, not zero. `charged_nano` includes upper holds for uncertain requests and must not be described as an invoice. Inspect source verification, actual final content and critique substance as well as the token totals.

An operational pass requires genuine Meta identities and inference, real substantive source/target coverage, recorded prior-art search (limitations allowed), at least one substantive valid independent critique, provisional labels, settled locally attributable requests, no unresolved reservations, correct direction associations, pause/resume and exact replay. A zero-hypothesis result can be scientifically appropriate, but does not complete the operational critique gate. Diagnose before deciding whether a separately authorized bounded question is warranted. Do not weaken the gates or auto-run another qualification.

## 5. Resume only after a valid checkpoint; cache-only replay and final report

Confirm PAUSED / QUALIFICATION_CHECKPOINT, no attached worker, no unresolved RESERVED/UNCERTAIN request, valid source/evidence hashes and substantive independent critique. Only use the NEW root/ID and unchanged new manifest. Cache-only replay can be performed on each completed child before resume. An error/timeout checkpoint is not a valid continuation checkpoint. The historical sessions are forbidden even if a local report looks resumable.

```sh
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session resume "$QUAL_ID" \
  --providers "$PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$QUAL_ROOT" session report "$QUAL_ID" > "$QUAL_ROOT/final-report.json"
uv run python - "$QUAL_ROOT" "$QUAL_ROOT/final-report.json" <<'PYREPLAY'
import json, subprocess, sys
for dossier in json.load(open(sys.argv[2]))['dossiers']:
    subprocess.run([sys.executable, '-m', 'autodiscover.cli', '--root', sys.argv[1],
                    'discover', '--cache-only', '--run-id', dossier['packet']['run_id']], check=True)
PYREPLAY
```

Replay must preserve packet digest, request totals and evidence anchor with zero external calls. Compare local accounting against the provider ledger. Provider billing reconciliation and human semantic review remain external acceptance evidence. Any uncertain dispatch, incomplete critique, source integrity failure, manifest mismatch or unexplained charge leaves qualification pending/NO-GO.

## 6. Historical supervised 90-minute commands — deferred beyond this milestone

These unchanged 90-minute profiles use their original high/45s settings, not the new qualification settings. Do not infer readiness or silently retune saved sessions. A successful controlled live Meta qualification is the next milestone; fresh 90-minute configuration and separate authorization must be reviewed afterward. Use an attended Mac with power/network. `caffeinate -i` keeps the foreground process awake. No 90-minute run was launched during implementation.

```sh
uv run autodiscover session preflight --profile "$LONG_PROFILE" --providers "$LONG_PROVIDERS"
LONG_ROOT=$(mktemp -d "$PWD/runtime/discovery-capability-ninety-minute-XXXXXX")
printf '%s\n' "$LONG_ROOT"
caffeinate -i uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session start \
  --profile "$LONG_PROFILE" --providers "$LONG_PROVIDERS" --authorize-live --allow-network
```

Copy the printed session ID into a second terminal with the same directory, environment-file path, manifest and root variables:

```sh
LONG_ID=session-PASTE_THE_NEW_ID
uv run autodiscover --root "$LONG_ROOT" session status "$LONG_ID"
uv run autodiscover --root "$LONG_ROOT" session report "$LONG_ID" > "$LONG_ROOT/report.json"
uv run autodiscover --root "$LONG_ROOT" session pause "$LONG_ID"
uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session resume "$LONG_ID" \
  --providers "$LONG_PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$LONG_ROOT" session cancel "$LONG_ID" --confirm
```

Pause closes admission and drains to a checkpoint; wait for PAUSED before resuming. SIGINT/SIGTERM use the same cooperative boundary. Cancel immediately fences the session and cannot be resumed. An already dispatched request can still finish and be billed. Five consecutive branches without reviewed knowledge, a distinct provisional candidate or a useful reviewed critique/negative result stop exploration; unrelated new papers cannot reset this counter. Direction changes and stop reasons remain auditable in packets and branch outcomes. The 90-minute duration is a maximum, never a requirement to keep spending without progress.

## Evidence and failure recovery

SQLite `lab.sqlite3` plus WAL is authoritative; keep sidecars with an inactive root. `artifacts/` contains hashed captures/checkpoints/packets. Never edit reservations or their request identities to force continuation. `session report` and cache-only replay use read-only snapshots. After process death, inspect `status`, preserve the root and use the original ID/manifest for `resume`. Settled cached responses survive a crash before the next checkpoint. A changed stage policy or provider manifest cannot reuse the settled identity.

`REQUEST_RECONCILIATION_REQUIRED` means preserve the listed IDs/model/time and reconcile with the provider. Resume refuses unresolved RESERVED/UNCERTAIN requests; no automatic adjudication command is provided. Local mock recovery and virtual 90-minute evidence do not qualify fully unattended overnight operation. That remains NO-GO pending supervised live behavior, charge reconciliation and an operator reconciliation procedure. PR #2 remains draft and unmerged.
