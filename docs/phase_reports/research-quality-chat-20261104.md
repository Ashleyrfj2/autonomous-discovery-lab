# Chat-mode research quality v1 — implementation checkpoint (2026-11-04)

Status: **OFFLINE IMPLEMENTATION COMMITTED ON ISOLATED BRANCH; NOT WIRED TO LIVE DISCOVERY**.

## Repository authority

- New isolated branch: `chat/research-quality-v1-20261104`.
- Branch derived from remote `chat/registered-experiments-20261103` at `9bbf427c2d69a688d73db7b4e81303867ac6fa74`.
- The later user-reported local run commit `72304b5` is **not available on the remote**. We did not modify PR #2, main, live checkpoints, existing budgets or runtime evidence.
- Source: `src/autodiscover/research/quality.py`.
- CLI: `src/autodiscover/research/quality_cli.py`.
- Tests: `tests/unit/test_research_quality.py`.
- Specs: `docs/research_quality/EVIDENCE_FIRST_V1.md` and `docs/research_quality/BENCHMARK_V1.md`.

## What was implemented

1. Five versioned instruction strings: source finding extraction, cross-domain bridge analysis, hypothesis author, independent critic and recovery controller.
2. Typed `AtomicFinding` and `MechanismBridge` contracts; claim flags preserve experimental status.
3. Offline `screen_evidence`: fail closed for invalid source, invented quote, title-only evidence, wrong access level, reused IDs, unknown bridge IDs and unjustified cross-domain superiority.
4. Offline `decide_recovery`: hard invalid claims reject, distinct new evidence required to revise, query loops and exhausted revisions end inconclusively.
5. Offline CLI emits only status/codes, not source passages. No retrieval, inference or event ledger mutation.
6. Focused tests cover both reported failure patterns **using synthetic stand-ins**, not the actual user run packet.

## Verification boundary

- **20 focused tests passed** on isolated Python 3.13/Pydantic 2.x in this chat's container with contract stand-ins matching the remote `Citation`, `Evidence` and `Record` fields; local Python compileall also passed.
- Long lines were adjusted to at most 100 characters in the committed files.
- This is **not** the full repo's Python 3.12/uv/Ruff/Pyright/full pytest/build acceptance. Those remain unexecuted.
- Source files were fetched back from GitHub and confirmed present. No CI outcomes are used as proof.
- Semantic support, external prior-art equivalence, source ownership rechecks and real commercial evidence **remain distinct human/independent gates**.

## Before any merge or live wiring

1. On the Mac, inspect `git status`, preserve local commit `72304b5` and immutable original packet.
2. Integrate or cherry-pick only after reconciling with the newer local code; do not overwrite PR #2.
3. Run `uv run ruff check .`, `uv run pyright`, `uv run pytest -q tests/unit/test_research_quality.py`, `uv run pytest -q`, `uv build` and record exact SHA and outputs.
4. Reconstruct actual run failures using archived source snapshots; do not treat synthetic fixtures as the live transcript.
5. Wire source-bound finding extraction and review as immutable checkpoints, retaining existing catalog ownership/digest validation and zero-dispatch replay behavior.
6. Perform frozen A/B/C comparative evaluation with independent semantic annotations. No billable calls without explicit permission.

**Current live qualification:** unchanged. **Novelty:** unverified. **Commercial validation:** level 0. **PR #2:** unmerged. **Overnight operation:** not qualified.

Recovery: read the two `docs/research_quality` files, this report and actual local `AGENTS.md`, `docs/HANDOFF.md`, live packet and git history. Related [Notion handoff](https://app.notion.com/p/40eec84d128b8133a0cbc94fb267d760?pvs=204).
