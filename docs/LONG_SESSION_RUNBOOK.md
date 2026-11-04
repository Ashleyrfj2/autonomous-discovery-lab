# Long-session runbook

The foreground Mac process runs the research controller independently of Codex.
Use the controlled qualification profile first. Review its recorded evidence,
replay and billing before starting a supervised four-hour session.

## Credentials and configuration

Run commands from the repository checkout on `integration/long-session-readiness`.
Use Python 3.12 through `uv sync --locked`. The standard Meta manifest reads
`META_API_KEY` from the environment. Keep the key in an ignored, owner-readable
dotenv file or export it in your terminal. Avoid copying it into any profile,
command-line argument, output file or Git commit.

```sh
ADL_ENV=/path/to/your/ignored/provider.env
PROVIDERS=config/discovery-meta.json
```

If `META_API_KEY` is already exported, omit `--env-file "$ADL_ENV"` from the
commands below. Both profiles select Discovery-v2. Edit the nested
`discovery.objective` in a copy of the chosen profile before launch. The objective
may span industries. Registered `discovery.sources` may add allowlisted public
HTTPS documents. The default allows Crossref and Europe PMC search and sends
bounded public source excerpts to the configured standard-mode Meta models.

The routes are Spark 1.3 for planning and extraction, Spark 1.2 for authorship and
bridge analysis, and Wonder 1.0 for separate critique. The manifest pins the
rates, timeout, native structured output and reasoning settings. Baseten is
outside these profiles. The account model catalog establishes availability.
Successful structured inference still needs the controlled qualification.

## 1. Preflight and offline rehearsal

```sh
uv run autodiscover session preflight \
  --profile config/session-qualification.json --providers "$PROVIDERS"

uv run --env-file "$ADL_ENV" autodiscover session preflight \
  --profile config/session-qualification.json --providers "$PROVIDERS" \
  --check-model-access --allow-network

DRY_ROOT=$(mktemp -d)
uv run autodiscover --root "$DRY_ROOT" session dry-run \
  --profile config/session-qualification.json --providers "$PROVIDERS"
```

The first command uses local configuration. The optional second command issues
authenticated model-catalog GET requests. The third command uses the packaged
fixture provider and archive, no credentials or external fetches. The
qualification profile deliberately pauses after the first branch. Copy its
printed session ID to `DRY_ID` and exercise resume.

```sh
uv run autodiscover --root "$DRY_ROOT" session resume "$DRY_ID" \
  --providers "$PROVIDERS"
uv run autodiscover --root "$DRY_ROOT" session report "$DRY_ID"
```

| Profile | Wall-time limit | Branches | Attempts | Upper token estimate, including reasoning | Gross standard-rate estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `session-qualification.json` | 720 seconds | 2 | 20 | 531,200 | $1.45552 |
| `session-four-hour.json` | 14,400 seconds | 64 | 640 | 16,998,400 | $46.57664 |

These are conservative admission estimates based on configured context,
maximum completion and role rates. They describe the configured profiles
and exclude credits and discounted caching. Billing confirmation comes from
the provider. The stored output count includes reasoning when reported as
part of completion usage. Reasoning is shown separately for visibility.

Both profiles default to one concurrent branch, zero retries and no aggregate
dollar ceiling. An optional `aggregate_cost_ceiling_usd` is applied before
whole-branch admission using the conservative estimate. Configurable request
and token ceilings reserve an entire branch's upper allowance at admission.
A branch has a 240-second invocation bound and at most four searches. Paused
wall time counts against the session deadline. Profile caps are upper bounds
and may stop a session much earlier than its time limit.

## 2. Controlled live qualification

This command explicitly authorizes paid inference and public retrieval. Run it
only when ready to incur the estimated usage above. Keep this terminal
available. Save the printed `session-...` ID in `QUAL_ID`.

```sh
QUAL_ROOT=runtime/controlled-live
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session start \
  --profile config/session-qualification.json --providers "$PROVIDERS" \
  --authorize-live --allow-network
```

After the first branch closes, expect `PAUSED` with
`QUALIFICATION_CHECKPOINT` if no earlier stop applied. Check that the branch
has a source-bound packet and substantive advisory critique. Then resume from
a separate invocation using the same root, manifest and authorization flags.

```sh
uv run autodiscover --root "$QUAL_ROOT" session status "$QUAL_ID"
uv run --env-file "$ADL_ENV" autodiscover --root "$QUAL_ROOT" session resume \
  "$QUAL_ID" --providers "$PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$QUAL_ROOT" session report "$QUAL_ID"
```

Review `dossiers[].packet` for real public sources, exact evidence and an
independent model critique. A justified recovery should leave a new source
and revision receipt. A run without a recovery need can still qualify
operationally, with recovery coverage limited to the offline tests. Select a
completed child ID from the report and exercise cache-only replay.

```sh
uv run autodiscover --root "$QUAL_ROOT" discover --cache-only --run-id "$CHILD_ID"
```

Check that replay yields the dossier digest and leaves request counts and
event anchors unchanged. Compare locally calculated usage with the provider
ledger. Pause the qualification decision if there is an unresolved reservation,
missing substantive critique, invalid packet, manifest mismatch or unexplained
provider charge. Operational qualification does not establish novelty or
commercial viability.

## 3. Supervised four-hour launch

After the controlled qualification passes, preflight the four-hour profile.
Use a separate root and an attended Mac. `caffeinate -i` prevents idle system
sleep while the process runs. Preserve power and network access. Start the
process in a terminal and use another terminal for controls.

```sh
uv run autodiscover session preflight \
  --profile config/session-four-hour.json --providers "$PROVIDERS"

LONG_ROOT=runtime/discovery-four-hour
caffeinate -i uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session start \
  --profile config/session-four-hour.json --providers "$PROVIDERS" \
  --authorize-live --allow-network
```

Copy the printed ID to `LONG_ID`. Expect the session to stop on the first
applicable duration, branch, request, token, optional aggregate cost, provider
error or stagnation boundary. A stalled session stops after five consecutive
branches without newly bound substantive evidence or a unique provisional
candidate. Any unresolved provider dispatch pauses for reconciliation.
Up to the configured number of branch requests may already be in progress
when a stop is detected. The supplied profiles run serially.

```sh
uv run autodiscover --root "$LONG_ROOT" session status "$LONG_ID"
uv run autodiscover --root "$LONG_ROOT" session pause "$LONG_ID"
uv run --env-file "$ADL_ENV" autodiscover --root "$LONG_ROOT" session resume \
  "$LONG_ID" --providers "$PROVIDERS" --authorize-live --allow-network
uv run autodiscover --root "$LONG_ROOT" session cancel "$LONG_ID" --confirm
uv run autodiscover --root "$LONG_ROOT" session report "$LONG_ID" > "$LONG_ROOT/report.json"
```

Pause closes admission and lets active work reach a checkpoint boundary.
Wait for `PAUSED` before resuming. SIGINT and SIGTERM request the same
cooperative drain. Cancel fences off the session immediately and cannot be
resumed. An in-flight network request may still execute or incur provider
charges after cancellation. The ledger retains uncertain reservations.

## Evidence and recovery

- `$LONG_ROOT/lab.sqlite3` and its WAL contain the authoritative event and usage
  records. Keep the root with its sidecars when copying an inactive session.
- `$LONG_ROOT/artifacts/` holds content-addressed source snapshots, discovery
  checkpoints and typed packets. `checkpoints/` and `logs/execution.jsonl` are
  derived recovery aids.
- `session report` lists progress by branch, provisional candidates, negative
  decisions, source diversity, usage, failure receipts, packet digests and
  suggested follow-ups. Partial children retain their checkpoint references.
  Read-only reports and cache-only child replay issue no external requests.
- After a process exit, inspect status first. Use the same root, session ID and
  manifest to resume an active orphan or paused session. A changed provider
  manifest is rejected. A settled response can be replayed even if the next
  checkpoint was interrupted.
- For `REQUEST_RECONCILIATION_REQUIRED`, preserve the root and reconcile the
  listed reservation IDs, model, request key and time against the provider
  usage ledger. Resume refuses unresolved reservations. Leave ambiguous rows
  intact. There is no automated adjudication or ledger-override command.
- A new session is a separate execution with a new ID and its own allowance.
  Recover an existing ID through `resume` to avoid repeating work.
