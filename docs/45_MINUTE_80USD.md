# Extended 45-minute Meta research run — budget-first

**Status: IMPLEMENTED_UNVERIFIED; do not use paid launch until local checks pass.**

This is an opt-in extended profile intended to avoid the previously observed
`OUTPUT_TOKEN_LIMIT` on the Spark 1.2 hypothesis stage. It does NOT edit or
resume any prior qualification session. Keep original runtime roots untouched.

## Changes

- Hypothesis output (including hidden reasoning) from 8,192 to **16,384 tokens**.
- Hypothesis timeout: 110 seconds; provider transport maximum: 120 seconds.
- No practical branch/call/token ceiling within a 45-minute operation:
  profile uses high schema-allowed bounds, with a 2,700-second wall-time
  maximum and two consecutive provider failures still triggering stop.
- Research stagnation stops after 50 stagnant branches; safety checks and
  factual critique/novelty/commercial validation gates are unchanged.
- **$80.00 session-local upper-bound admission cap**, plus an atomic
  reservation-time check before *every* billable request. Outstanding
  reservations retain their maximum reserved amount, including UNCERTAIN.
- Both current 45-minute and older frozen profiles remain unchanged.
- No auto-retry for ambiguous provider results; no artificial provider
  result expansion or validation bypass.

## IMPORTANT: billing boundary

Meta states that its Model API currently has **no enforceable account spend
limit**, only alerts; see https://dev.meta.ai/help/billing/spend-limit-alert .
The guard above is LOCAL to a single newly registered session root, not a
provider invoice cap or global cost aggregation across prior sessions, other
API keys, simultaneous processes, playground requests or other applications.
One account may exceed $80 overall even if a new session does not.

The local reservation uses the configured context upper bound and full
completion including reasoning, at recorded pricing. This intentionally
overestimates typical request cost; unexpected provider price changes or
account-wide charges are outside the local guarantee. If $80 means TOTAL
Meta account spend, check Meta Usage/Billing and subtract prior/unknown
charges before choosing a lower session cap.

## Non-billable validation

```sh
cd ~/Code/autonomous-discovery-lab
git fetch origin
git switch --track origin/feat/45m-80usd-cap-20261104
uv sync --locked
uv run pytest -q tests/unit/test_45_minute_launch.py
uv run pytest -q
uv run ruff check .
uv run pyright
uv build

PROFILE=config/session-capability-forty-five-minute-80usd.json
PROVIDERS=config/discovery-capability-meta-extended-20261104.json
uv run autodiscover session preflight --profile "$PROFILE" --providers "$PROVIDERS"
ROOT=$(mktemp -d)
uv run autodiscover --root "$ROOT" session dry-run \
  --profile "$PROFILE" --providers "$PROVIDERS"
```

## Billable qualification (only after owner approval)

Do not resume the prior failed session. Validate the provider's practical
support for 16,384 completion tokens on a fresh single-branch root first,
then inspect its checkpoint evidence. A separate one-branch preflight with
the extended manifest may be used, with matching model identities and a
bounded budget; do not automatically rerun failed requests.

A full 45-minute launch must use a NEW root. Keep the returned session ID,
check usage periodically and stop on provider billing mismatch, uncertain
requests or the absence of meaningful findings.
