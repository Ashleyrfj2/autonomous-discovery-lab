# Reviewed experiment registry: encoding-v1 and allocation-v1

Status: **IMPLEMENTED_UNVERIFIED (ChatGPT GitHub branch)**. Implementation and tests have been committed remotely, but local Python 3.12/Mac sandbox qualification has NOT been run. This is a second *reviewed scientific experiment family*, not a claim of scientific novelty or a general code-generation sandbox.

## System boundary and migration strategy

- The original `encoding-v1` `Plan`, encoding worker, fixture generator and independent evaluator files remain unchanged so their preregistered worker/fixture/evaluator digests continue to refer to the previously reviewed source.
- `src/autodiscover/experiments/registry.py` is a fixed allowlist containing exactly two families, including worker/fixture/evaluator file identities. No model, prompt, API request or user input may register a Python script or evaluator.
- `allocation-v1` uses a separate `AllocationPlan`, reproducible fixture generator, isolated standard-library worker and independent evaluator. Both families dispatch through the existing macOS Seatbelt supervisor, job fencing, bounded concurrency, cancellation, immutable event evidence, and source hash assertions.
- The full `Lab.explore` lifecycle can register both reviewed hypothesis kinds, select across them, preregister plans, preflight workers, store raw outputs, recompute independent evaluations, replicate, and leave market validation at level 0.
- Hypothesis revisions for allocation-v1 are deliberately not auto-generated. No unreviewed mutation is permitted, and model-suggested strategies remain theoretical until a reviewed adapter exists.
- Existing scored results use **family-specific** metrics. The director allocates across families before exploiting scores within a family. A score from compression is not scientifically comparable to allocation gain.

## Allocation-v1 protocol

The new family solves **bounded 0/1 allocation** with a capacity constraint, comparing a reviewed dynamic-programming candidate against a ratio-greedy baseline. Each input is a seeded set of at most 12 items (integer weight/value) and capacity at most 100. The selected indices must be sorted/unique and the total weight within capacity.

Independent validation enumerates all possible subsets using separate code (not the worker's DP). It rejects malformed indices, duplicate selections, overweight allocations, plan/digest/replication changes, impossible results and mismatches between preregistered source hashes and the current reviewed source.

Train/held-out allocation traps (default six train, twelve heldout per replication) are generated with deterministic shuffling, and the exact dynamic optimum is compared against the ratio-greedy baseline. The preregistered default success criterion requires all held-out cases optimal and each held-out normalized improvement at least 15%. Two independently seeded replications follow. This is a *deliberately simple known-problem proof* of the family registry/evaluator; it does not establish generalized scheduling skill, new discoveries, frontier search or applicability to real buyers.

## Commands

```sh
# Existing encoding workflow remains unchanged.
uv run autodiscover --root runtime/demo-encoding demo

# Reviewed new family; pure local computation, no Meta/Baseten inference.
uv run autodiscover --root runtime/demo-allocation allocation-demo \
  --topic "regional resource allocation" --algorithm dynamic

# Deliberate negative baseline; MUST NOT be reported as scientific success.
uv run autodiscover --root runtime/demo-baseline allocation-demo \
  --topic "regional resource allocation" --algorithm greedy

# Native job/branch/integrity checks on the returned run ID:
uv run autodiscover --root runtime/demo-allocation status RUN_ID
uv run autodiscover --root runtime/demo-allocation tree RUN_ID
uv run autodiscover --root runtime/demo-allocation jobs RUN_ID
uv run autodiscover --root runtime/demo-allocation integrity
```

Do not run these against an existing user's persisted runtime root before testing on fresh temporary roots. The runner fails closed on unsupported platforms; the current macOS Seatbelt implementation remains a nonproduction trust boundary. No execution from a remote web request or a model-provided filename is supported.

## Model role separation and criticism

`src/autodiscover/models/teams.py` provides an **opt-in** three-route `ResearchTeam` calling the existing budget-accounted `Router` with distinct provider/model identities:

- `RESEARCH_PROPOSALS`: a typed proposal with falsifiable prediction and source IDs.
- `EXPLORATORY`: a distinct candidate model and its own typed proposal.
- `CRITIQUE`: a different model critiques assumptions, methods and alternative explanations for each candidate, and proposes a disconfirming experiment.

The result is not an experimental conclusion. The schema requires `novelty_verified=false`, `technical_verified=false`, and `commercial_validated=false`; source IDs must be among valid run-owned records. Private/operator-imported, mock and legacy-unverified text is blocked from automatic model sharing; recognizable tokens in the input block routing. No model can approve payment evidence or turn a critique into scientific acceptance.

**Do not instantiate a live ResearchTeam until the operator separately configures/authorizes its providers, trusted source-sharing rules, current capabilities/rates and spending limits.** No live provider runs were executed by this branch.

## Cost-aware planning

`src/autodiscover/hypotheses/portfolio.py` is a read-only budget-aware planner that accepts bounded *predictions* of cost, time, information gain, uncertainty and estimate provenance. Independently calibrated estimates require a digest; weaker operator/model estimates are discounted. Outputs include budget usage estimates, selected/excluded candidates and an explicit `execution_authorized: false`.

```sh
uv run autodiscover portfolio-plan portfolio-request.json
```

Example request:

```json
{
  "budget_usd": "0.50",
  "seconds_budget": 60,
  "max_experiments": 2,
  "candidates": [
    {
      "candidate_id": "A",
      "family": "encoding-v1",
      "estimated_max_cost_usd": "0.05",
      "estimated_seconds": 10,
      "expected_information_gain": 0.4,
      "uncertainty": 0.3,
      "provenance": "operator_estimate"
    },
    {
      "candidate_id": "B",
      "family": "allocation-v1",
      "estimated_max_cost_usd": "0.10",
      "estimated_seconds": 20,
      "expected_information_gain": 0.5,
      "uncertainty": 0.2,
      "provenance": "model_estimate"
    }
  ]
}
```

The portfolio planner does NOT directly mutate the director, enqueue jobs, increase budgets, make provider calls, or authenticate scientific results. Integrating calibrated risk-aware predictions into the durable director would require adding evidence-backed estimate fields and replay-safe migrations; this is deliberately deferred rather than granting untrusted model predictions execution authority.

## Required acceptance on the Mac

```sh
uv run ruff check .
uv run pyright
uv run pytest -q tests/integration/test_registered_experiments.py tests/unit/test_model_team_portfolio.py
uv run pytest -q
uv build
```

Then run the three separate CLI fresh-root demonstrations above; review raw results, independent recalculation, complete stage/replication histories, stored budgets, and hash-chain verification. Test stop/resume and active-worker cancellation for allocation-v1; repeat on a fresh clone with exact source SHA. The historical 175-test Phase 9 backend result is not acceptance for this branch. GitHub Actions alone are not a release gate.

## Remaining

1. Local qualification and repair of any regression.
2. Real source-grounding/prior-art assessment (separate draft PR for source-bound dossier; not included here).
3. Calibrated cost/utility policies and real provider comparisons; do not trust self-estimated information gains.
4. Additional genuinely varied task families with independently reviewed evaluators; avoid fake diversity from changing domain names.
5. Full Phase 9 12ui export and browser acceptance; separately authorized live-provider runs, extended soak, production security and external commercial validation.
