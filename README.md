# Autonomous Discovery Lab

**An experimental AI research system that investigates questions, proposes testable hypotheses, challenges its own reasoning, and keeps an auditable record of what was actually verified.**

Built for the **Meta Global AI Developer Hackathon 2026**.

## For judges: choose your setup

**There are two ways to run the research system.** For the actual **Meta model-powered research workflow**, use **Option A (Live Meta API)**. For a reproducible scripted demonstration without live inference, use **Option B (Offline rehearsal)**. Both use the same research-session controller and evidence/reporting system, but they are **not equivalent**: the offline path does not make model calls or demonstrate live AI reasoning.

| | Option A — Live Meta API | Option B — Offline rehearsal |
| --- | --- | --- |
| Meta API key | **Required** | Not used |
| Model inference | Real calls to configured Meta models | Scripted model responses |
| Internet | Required for Meta calls and public research retrieval | Not required |
| Potential API costs | **Yes**; review usage and your own account balance | No model API charges |
| Main purpose | Evaluate the AI-driven research workflow | Verify the controller, outputs, saved state, and reporting |

This is a **local Python command-line application**, not a hosted website. If you want to inspect independently evaluated technical experiments, see **Option C** below. Those locally executed experiments use reviewed benchmark workers rather than live Meta inference.

### Requirements

- **Python 3.12** (the project requires `>=3.12,<3.13`).
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for installation and execution.
- A terminal. The reviewed sandboxed experiment demos in Option C require **macOS Seatbelt**; the research-session commands use the project CLI.
- **Option A:** your own Meta API key with access to the configured models and valid billing/credits. **Option B:** no provider credentials.

### Step 1 — Install

```bash
git clone https://github.com/Ashleyrfj2/autonomous-discovery-lab.git
cd autonomous-discovery-lab
uv sync --locked
uv run autodiscover check
```

If you are reviewing an archive instead of a GitHub clone, open its project directory before running `uv sync --locked`.

### Option A — Live Meta API research (real model calls)

Choose this to see Meta models perform research planning, evidence extraction, gap analysis, hypothesis development, and adversarial critique. The provider configuration routes work to **Muse Spark 1.3**, **Muse Spark 1.2**, and **Muse Wonder 1.0**. Access to all three models must be enabled on your Meta account. A research run may pause, reject hypotheses, or stop without a validated discovery.

**1. Set up your own Meta API credential.** The live option **will not work without `META_API_KEY`**. Choose **one** method:

**Method 1 — Export the key in the terminal you are using:**

```bash
export META_API_KEY="PASTE_YOUR_OWN_META_API_KEY_HERE"
```

Replace the placeholder with an actual Meta key that has access to all three configured models. Do not leave the placeholder unchanged, and do not share your key in screenshots or logs.

**Method 2 — Use a private `.env` file:** Create a file named `.env` in this repository (or use your existing local credential file) containing:

```dotenv
META_API_KEY=YOUR_OWN_META_API_KEY
```

The project's `.gitignore` excludes `.env`. If using this method, **you must add `--env-file .env` to every `uv run` command requiring Meta credentials**; a regular `uv run` will not necessarily load it. Replace `.env` with the correct full path if the file is elsewhere. Do not commit credentials.

**2. Preflight and verify model access before attempting a live run.**

```bash
PROFILE=config/session-capability-qualification-evidence-v3.json
PROVIDERS=config/discovery-capability-meta-medium-v2.json

# Local configuration validation only; succeeds even if the key is missing.
uv run autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS"
```

**Check which credential method you are using (this never displays the key):**

```bash
if [ -n "${META_API_KEY:-}" ]; then
  echo "META_API_KEY is available in this terminal"
elif [ -f .env ]; then
  echo "Found .env — use the --env-file .env form below"
else
  echo "No exported META_API_KEY and no .env in this directory"
fi
```

**Then run ONE authenticated model-access check:**

With **Method 1** (exported key):

```bash
uv run autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS" \
  --check-model-access --allow-network
```

With **Method 2** (`.env` file):

```bash
uv run --env-file .env autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS" \
  --check-model-access --allow-network
```

The local preflight prints the configured model routes, admission limits, and estimated maximum costs. **It does not test credentials.** The authenticated command checks the model catalog and should return `model_access` results for all three roles. If you see `Invalid or inaccessible session profile, provider manifest or credentials.`, confirm the key was actually loaded first. If it was loaded, check the file path, Meta model entitlements and account access. This error is generic; it does not, on its own, prove which of those failed. The catalog check does not perform research inference.

**3. Start a fresh, operator-authorized Meta qualification session (billable).**

Only run this after reviewing the preflight cost estimate, available credit, and potential external billing. The included qualification profile can run **up to 3,000 seconds**, admits at most **2 research branches**, and has a **conservative gross estimate of $3.787648 at the rates recorded in the configuration**. **That estimate is not a hard provider billing cap or a guarantee of the final charge.** The session may pause or end early.

```bash
META_ROOT=$(mktemp -d)
printf 'Saved evidence directory: %s\n' "$META_ROOT"

uv run autodiscover --root "$META_ROOT" session start \
  --profile "$PROFILE" --providers "$PROVIDERS" \
  --authorize-live --allow-network
```

**Using a `.env` file instead?** Replace `uv run autodiscover` with `uv run --env-file .env autodiscover` for the live `session start` command, and for any later live `session resume`. The `session status` and `session report` commands are local/read-only and do not need the key.

Save the **session ID** printed by the CLI. The first branch is configured to pause for a qualification checkpoint. Inspect the report **before** resuming or requesting more paid calls:

```bash
META_ID="PASTE_PRINTED_SESSION_ID_HERE"
uv run autodiscover --root "$META_ROOT" session status "$META_ID"
uv run autodiscover --root "$META_ROOT" session report "$META_ID"
```

If the session is legitimately paused, **only after checking** evidence integrity, the critique, usage, and that there are **no unresolved or uncertain requests**, you can continue the **same** session:

```bash
uv run autodiscover --root "$META_ROOT" session resume "$META_ID" \
  --providers "$PROVIDERS" --authorize-live --allow-network
```

Do not start another session to resume an existing one. If provider activity times out or its billing status is uncertain, **do not blindly retry**; preserve the saved root for reconciliation. For pause, cancellation, replay, and detailed qualification gates, use the [operator runbook](docs/LONG_SESSION_RUNBOOK.md). Do not run the longer 45- or 90-minute experimental profiles as a replacement for this short qualification without their separate acceptance steps.

**What to inspect:** source provenance and gaps, each Meta model's role, the generated candidates, the independent critic's objections, rejected/retained hypotheses, checkpoint/recovery state, usage ledger and evidence report. A Meta model's answer is never counted as independent technical proof.

### Option B — Offline research rehearsal (scripted, no Meta calls)

Use this when you cannot access the live Meta API, want to review the controller, or prefer a no-cost reproduction. This exercises the research workflow with **scripted** inputs and responses; it is **not** the full live AI functionality.

```bash
PROFILE=config/session-capability-qualification-evidence-v3.json
PROVIDERS=config/discovery-capability-meta-medium-v2.json

# Inspect research roles and limits, without a credential or inference.
uv run autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS"

# Keep this run's reports and evidence in a new, isolated directory.
SESSION_ROOT=$(mktemp -d)
uv run autodiscover --root "$SESSION_ROOT" session dry-run \
  --profile "$PROFILE" --providers "$PROVIDERS"
```

Copy the **session ID** printed by the CLI to inspect its saved report:

```bash
SESSION_ID="PASTE_PRINTED_SESSION_ID_HERE"
uv run autodiscover --root "$SESSION_ROOT" session status "$SESSION_ID"
uv run autodiscover --root "$SESSION_ROOT" session report "$SESSION_ID"
```

**What to inspect:** the research stages, simulated evidence, candidate hypotheses, critique/rejection reasons, stopping conditions, and recorded usage. The scripted rehearsal is not evidence of live Meta quality or a new discovery.

### Option C — Run a reviewed technical experiment (macOS)

The project includes two *reviewed, preregistered* benchmark families: lossless encoding (`encoding-v1`) and constrained resource allocation (`allocation-v1`). The allocation worker is checked by a **separate evaluator** against an exact solution on held-out cases, with replication and durable evidence.

```bash
# Positive experiment: reviewed dynamic-programming approach.
ALLOC_ROOT=$(mktemp -d)
uv run autodiscover --root "$ALLOC_ROOT" allocation-demo \
  --topic "regional resource allocation" --algorithm dynamic

# Negative control: greedy baseline is expected to fail the improvement gate.
GREEDY_ROOT=$(mktemp -d)
uv run autodiscover --root "$GREEDY_ROOT" allocation-demo \
  --topic "regional resource allocation" --algorithm greedy

# Alternate reviewed family: local lossless encoding experiment.
ENCODING_ROOT=$(mktemp -d)
uv run autodiscover --root "$ENCODING_ROOT" demo
```

Each command prints a JSON report containing its **run ID**. For example, inspect the dynamic allocation run with:

```bash
RUN_ID="PASTE_ALLOCATION_RUN_ID_HERE"
uv run autodiscover --root "$ALLOC_ROOT" status "$RUN_ID"
uv run autodiscover --root "$ALLOC_ROOT" tree "$RUN_ID"
uv run autodiscover --root "$ALLOC_ROOT" jobs "$RUN_ID"
uv run autodiscover --root "$ALLOC_ROOT" integrity
```

**What to inspect:** the positive result versus the deliberately failing control; preregistered plans and worker/evaluator identities; held-out evaluation and replications; job lineage; and the verifiable event chain. Do **not** compare numeric scores across unrelated experiment families as if they meant the same thing.

See [reviewed experiment protocol](docs/REGISTERED_EXPERIMENTS.md) and [local test and replay evidence](docs/phase_reports/pr-2-local-verification.md).

### Optional — Run project checks

```bash
uv run pytest -q
uv run ruff check .
uv run pyright
uv build
```

These commands verify tests, linting, type checking and package builds. They may require the intended local platform or test fixtures. Past acceptance results are documented in the linked phase reports; **a past test pass is not a claim that every later commit or optional live configuration has been qualified**.

## Why Meta's models matter

The **live AI-native research path** uses separate model roles rather than asking one model to make and approve its own discoveries:

| Research responsibility | Configured Meta model | Role |
| --- | --- | --- |
| Planning and extraction | **Muse Spark 1.3** | Identify research directions and organize source-grounded evidence |
| Gap analysis and hypothesis proposal | **Muse Spark 1.2** | Examine constraints, challenge whether AI is necessary, and propose testable mechanisms |
| Independent adversarial critique | **Muse Wonder 1.0** | Challenge assumptions, explanations, evidence and experimental design |

The engine then enforces deterministic rules for evidence ownership, provenance, accepted experiment families, spending reservations, durable checkpoints and replay. **A model critique is not a scientific proof.** Empirical validation, novelty, and customer demand are separate gates.

The sample Meta manifest is [`config/discovery-capability-meta-medium-v2.json`](config/discovery-capability-meta-medium-v2.json).

### Live API configuration and authorization

**Live setup is Option A at the top of this README.** Meta API credentials are required for actual model-driven discovery. The offline rehearsal is a separate fallback, not a substitute for using Meta models. See the [live operator runbook](docs/LONG_SESSION_RUNBOOK.md) for permission, usage, recovery, and evidence-qualification checks.

## How the system works

1. **Select a research question.** The system can explore AI-enabled capabilities or open scientific problems rather than being fixed to one industry.
2. **Collect and qualify sources.** Public bibliographic evidence is tracked with provenance and explicit gaps. Retrieval is not exhaustive prior-art proof.
3. **Generate candidate hypotheses.** Model outputs describe mechanisms, assumptions, predictions and potential falsification tests.
4. **Challenge the candidates.** A distinct critic looks for unsupported claims, alternatives and missing evidence.
5. **Experiment where reviewed evaluators exist.** Only allowlisted local experiment families can execute; the model cannot submit arbitrary Python code for execution.
6. **Independently evaluate and replay.** Results, source identities, model usage, failures and decisions are stored for inspection. Scientific acceptance and commercial validation are never inferred from model confidence.

### Current boundaries — important

- **Demonstrated locally:** reviewed benchmark experiments, negative controls, state persistence, testable recovery paths, provenance/integrity verification, and scripted research-session workflows. Specific historical acceptance results are in the phase reports.
- **Partially qualified:** live Meta research behavior and model-role configuration; earlier bounded qualifications exist, but not every optional profile, full-session duration or scientific quality claim is validated.
- **Not established:** an independently verified novel scientific discovery, an exhaustive novelty search, general-purpose execution of arbitrary AI-written experiments, real customer willingness to pay, or production deployment.
- **No hosted demo is promised by this README.** The primary supported judge interface is the CLI.

## Further reading

- [AI-native research method and verification evidence](docs/phase_reports/AI_NATIVE_DISCOVERY_2026-11-04.md)
- [Evidence-role repair and its limits](docs/phase_reports/EVIDENCE_ROLES_REPAIR_2026-11-04.md)
- [Experiment-family design, evaluator and controls](docs/REGISTERED_EXPERIMENTS.md)
- [Local audit results for the experiment registry](docs/phase_reports/pr-2-local-verification.md)
- [Live qualification and operator controls](docs/LONG_SESSION_RUNBOOK.md)
- [Release readiness and remaining work](docs/RELEASE_READINESS.md)

**Short version:** this project is intended to make AI-generated research *testable and auditable*. The most important distinction in judging it is between **what an AI suggested**, **what an independent test verified**, and **what is still unknown**.
