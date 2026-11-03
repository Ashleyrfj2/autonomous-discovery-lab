# Decision log

## DEC-001 — 2026-11-03 — Isolated repository
Problem: current workspace is an empty repository named research, not the requested project. Alternatives: repurpose it or create an isolated nested repository. Selected: `autonomous-discovery-lab/` with its own Git history. Evidence: initial audit found only `.git`, no commits or project files. Tradeoff: nested checkout requires explicit working directory. Affected: all. Revisit only with user repository-location direction.

## DEC-002 — 2026-11-03 — Trusted experiment implementations first
Problem: arbitrary generated code requires stronger isolation than ordinary processes or Docker. Alternatives: arbitrary-code container, remote sandbox, reviewed allowlist. Selected: reviewed fixed workers only; no executable model input; deny unauthorized file/network operations by eliminating those capabilities from the worker contract, enforce OS resource bounds and controlled environment. Tradeoff: MVP experiments cover a bounded family, while the research/hypothesis pipeline remains cross-industry. Affected: experiments/security. Revisit when a genuinely isolated execution provider is available and authorized.

## DEC-003 — 2026-11-03 — Local deterministic acceptance
Problem: no live provider authorization or current credentials established. Selected: mock development and HTTP contract tests, explicit configuration for live use, no live calls. Technical/source novelty/market gates stay distinct. Tradeoff: cannot claim live provider acceptance. Revisit with authorized credential and budget configuration.
