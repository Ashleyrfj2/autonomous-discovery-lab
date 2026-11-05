# 45-minute supervised discovery — launch candidate

Status: IMPLEMENTED_UNVERIFIED. This branch was authored via the GitHub connector;
local tests and a live independent Meta critique are required before launch.
This is a **maximum 45-minute** run, not a guaranteed 45 minutes of activity
or a guarantee of a new invention. It stops earlier on stagnation, errors,
admission limits, operator cancellation or ambiguous provider dispatch.

## What is different

- New opt-in `config/session-capability-forty-five-minute.json` uses the
  evidence-v3/capability-v2 research contract. Earlier profiles and archived
  sessions must not be edited or resumed.
- Real capability-v2 bibliography capture screens obvious off-topic titles
  before the extractor; when Crossref yields no relevant substantive abstract,
  Europe PMC can supply an alternative. This lexical triage is deliberately
  conservative, not proof of factual relevance. Title-only leads never count
  as empirical support. Live records carry explicit low-relevance failures.
- Combined source/target/prior-art search prefers substantive abstracts to
  title-only leads when composing the model's bounded evidence context.
- Future branches receive bounded, durable, unreviewed-labeled questions,
  failure reasons and targeted queries from closed prior branches; no
  unsupported assertion becomes a validated finding by repetition.
- The existing deterministic evidence-role checks, independent critique,
  anti-duplicate logic, journal, replay, cancellation and uncertain-request
  handling remain intact.

## Limits and expectations

Profile: 2,700 seconds maximum session duration; one request concurrently;
eight branches maximum; 104 model calls and 5,614,592 combined
input/completion tokens maximum, both conservative admission envelopes.
Up to 1,200 seconds per branch with low/low/medium/medium/medium reasoning
and 90/45/60/90/90-second request timeouts. Five stagnant branches or
two consecutive provider errors stop the run.

Conservative pricing at retained standard rates: $1.893824 per branch,
$15.150592 across eight branches; new admission ceiling $15.20.
This is an admission-bound estimate and is NOT a verified invoice, Meta
credit balance, or automatically effective dollar charge cap during an
already admitted branch. The controller may stop well before 45 minutes
if progress or funding bounds are reached.

The old timed-out reservation remains UNCERTAIN; provider billing is
unverified. Do not modify those preserved historical records.

## Gate 1 — Local acceptance (not billable)

Use the primary synced main checkout, create/switch to this feature branch
locally when ready, and inspect the diff before testing.

```sh
cd ~/Code/autonomous-discovery-lab
git fetch origin
git switch --track origin/feat/45m-research-launch-20261104
uv sync --locked
uv run pytest -q tests/unit/test_45_minute_launch.py
uv run pytest -q
uv run ruff check .
uv run pyright
uv build
```

If any local check fails, do not run live inference. Do not use failing
GitHub Actions startup/quota as a substitute for local testing.

## Gate 2 — Preflight and offline rehearsal (not billable)

```sh
ADL_ENV="$HOME/Code/autonomous-discovery-lab/.env"
PROVIDERS=config/discovery-capability-meta-medium-v2.json
PROFILE=config/session-capability-forty-five-minute.json

uv run autodiscover session preflight --profile "$PROFILE" --providers "$PROVIDERS"
uv run --env-file "$ADL_ENV" autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS" --check-model-access --allow-network

DRY_ROOT=$(mktemp -d)
uv run autodiscover --root "$DRY_ROOT" session dry-run \
  --profile "$PROFILE" --providers "$PROVIDERS"
```

The model catalog check is read-only. Dry-run uses scripted models and cannot
establish real-world discovery performance, 45-minute stability, or quality.

## Gate 3 — Real independent critic

The existing evidence-v3 live checkpoint returned zero critiques. Before
calling this launch ready, run a separately authorized bounded Meta check
using a real evidence-supported research question, inspecting that the real
CRITIQUE identity (Muse Wonder 1.0) independently evaluates source claims.
The critic may legitimately reject a weak hypothesis; it need not certify
novelty. Mock critique alone is not this gate. Document the result, provider
receipt and any missing evidence. If a safe bounded procedure is not yet
available, this remains BLOCKED and the 45-minute session is NO-GO.

## Gate 4 — Explicitly authorized live 45-minute run

Only after Gates 1–3 pass and the operator accepts potential API charges:

```sh
RUN_ROOT=$(mktemp -d "$PWD/runtime/controlled-discovery-45m-XXXXXX")
printf 'Runtime root: %s\n' "$RUN_ROOT"
caffeinate -i uv run --env-file "$ADL_ENV" autodiscover --root "$RUN_ROOT" \
  session start --profile "$PROFILE" --providers "$PROVIDERS" \
  --authorize-live --allow-network
```

Preserve the printed session ID. Do not `session start` again to resume.

```sh
RUN_ID=session-PASTE_PRINTED_ID
uv run autodiscover --root "$RUN_ROOT" session status "$RUN_ID"
uv run autodiscover --root "$RUN_ROOT" session report "$RUN_ID" > "$RUN_ROOT/report.json"
```

Inspect source relevance, evidence anchors, per-request settled/uncertain
receipts, review authenticity, novel mechanisms versus prior art, useful
negative findings and reasons for research stagnation. Any RESERVED/UNCERTAIN
request blocks automatic resume. Use the existing long-session runbook for
cache-only replay and pause/cancel handling.

A successful run may end with zero accepted new hypotheses; report that as
an honest discovery result. Do not label retrieved papers, prompt-generated
speculation or provisional tests as independently proven inventions.
