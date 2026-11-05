# Autonomous Discovery Lab

**An experimental AI research system that investigates questions, proposes testable hypotheses, challenges its own reasoning, and keeps an auditable record of what was actually verified.**

Built for the **Meta Global AI Developer Hackathon 2026**.

## For judges: start here

**Fastest way to evaluate this project:** run the no-key research-session rehearsal in **Step 2**. If you have a Mac, also run the independently evaluated experiment in **Step 3**. Neither workflow sends requests to Meta, uses paid APIs, or requires a credential.

This is a **local Python application with a command-line interface**, not a hosted website. The offline rehearsal demonstrates the workflow and evidence handling using scripted model outputs; it **does not** demonstrate live Meta reasoning. The reviewed experiment demonstrates real local execution and independent evaluation on a known benchmark; it **does not** establish that the system discovered a new scientific result.

### Requirements

- **Python 3.12** (the project currently requires `>=3.12,<3.13`).
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency installation and commands.
- A terminal. **macOS is required for the native sandboxed experiment demos** (they use macOS Seatbelt). The session preflight and scripted dry-run do not require a Meta key.
- No API key, account, or paid inference for the recommended evaluation path.

### Step 1 — Install

```bash
git clone https://github.com/Ashleyrfj2/autonomous-discovery-lab.git
cd autonomous-discovery-lab
uv sync --locked
uv run autodiscover check
```

If you are reviewing an archive instead of a GitHub clone, open its project directory before running `uv sync --locked`.

### Step 2 — Run the AI research workflow without an API key (recommended)

This uses the project's scripted providers to exercise the **planning → evidence processing → hypothesis → independent critique → durable report** workflow. It is an **offline simulation**, not a real Meta API call.

```bash
PROFILE=config/session-capability-qualification-evidence-v3.json
PROVIDERS=config/discovery-capability-meta-medium-v2.json

# Check the exact research roles, bounds, model configuration and cost estimates.
uv run autodiscover session preflight \
  --profile "$PROFILE" --providers "$PROVIDERS"

# Use a new directory so the judge's run cannot overwrite existing evidence.
SESSION_ROOT=$(mktemp -d)
uv run autodiscover --root "$SESSION_ROOT" session dry-run \
  --profile "$PROFILE" --providers "$PROVIDERS"
```

The dry-run prints a **session ID** and a JSON outcome. Copy that ID to inspect the saved result:

```bash
SESSION_ID="PASTE_SESSION_ID_HERE"
uv run autodiscover --root "$SESSION_ROOT" session status "$SESSION_ID"
uv run autodiscover --root "$SESSION_ROOT" session report "$SESSION_ID"
```

**What to inspect:** the research stages, sources and evidence limitations, candidate hypotheses, critique/rejection reasons, stopping conditions, and recorded usage. A rejected or unverified hypothesis is a valid outcome; a generated idea is not automatically marked as a discovery.

### Step 3 — Run a verified technical experiment (macOS)

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

### Step 4 — Run project checks (optional)

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

### Optional: check live model access

**Not necessary for judging the offline demo.** A live check requires your own Meta API credentials and network access:

```bash
export META_API_KEY="YOUR_OWN_KEY"

uv run autodiscover session preflight \
  --profile config/session-capability-qualification-evidence-v3.json \
  --providers config/discovery-capability-meta-medium-v2.json \
  --check-model-access --allow-network
```

This checks the model catalog, **not** whether a full live research session will succeed. Do not include or commit an API key. A real research session can generate charges; it must be explicitly authorized with live flags, a **fresh runtime root**, an operator-reviewed budget, and the controls in the [long-session runbook](docs/LONG_SESSION_RUNBOOK.md). Do not resume archived historical sessions. The experimental 45-minute launch configurations remain subject to their own acceptance gates; they are **not** the recommended judging path.

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
