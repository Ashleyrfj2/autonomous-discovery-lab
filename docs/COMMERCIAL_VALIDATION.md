# Commercial evidence protocol

Technical performance, discovery novelty and market validation are independent. A benchmark, model-generated demand estimate, synthetic interview or simulated customer never counts as external commercial evidence.

Opportunity profiles contain a target user, economic buyer, problem and severity, current alternatives, competition, adoption constraints, buyer reachability and explicit assumptions. Empty fields remain unknown. Competitor descriptions without an actual source name mention remain hypothetical; a mention is not proof of competitive advantage.

The service accepts source-bound evidence records and recomputes these levels:

- **0:** hypothetical opportunity, or insufficient qualifying external evidence.
- **1:** operator-reviewed external evidence of a real problem.
- **2:** qualifying direct prospective-user or buyer evidence, plus real-problem evidence.
- **3:** serious adoption or pilot commitment, plus real-problem evidence.
- **4:** payment or comparably strong commercial commitment, plus real-problem evidence and identified user/buyer roles. Payment records need a positive amount, currency and matching buyer role.

External evidence needs an exact quote from a primary document whose provenance is a live HTTPS fetch or an explicit operator document import. Metadata-only sources, known mock fixtures and legacy records without provenance cannot qualify. Merely collecting a document or attaching a citation does not raise its level.

Reviews are a separate authority boundary: model/system actors cannot attest commercial facts. The trusted operator entry point records source-bound human decisions and rationale as immutable artifacts with append-only events. The CLI requires an interactive terminal and an explicit typed confirmation; piped approval is refused. Future dashboard controls must preserve that operator boundary and must not expose review authority as an inference tool.

These gates rely on truthful human attestation of the original document. They do not automatically authenticate interviews, verify a payment processor transaction or establish business viability. A user can supply false documents or a dishonest review; local hashes do not solve that trust problem. Never present a classification test fixture as a real customer, pilot or payment.

Review withdrawals, invalidated sources and changed opportunity profiles affect the current assessment. Reports retain the original recorded stage level separately, show the current level, and keep technical/novelty results independent. Evidence/review origin, ordering, ownership and current-profile projections are checked against the hash-chained event history.

CLI operations (local runtime; no messages or payments are sent):

```sh
uv run autodiscover --root runtime market-opportunity RUN_ID opportunity.json
uv run autodiscover --root runtime market-document RUN_ID source.txt --title 'Operator document'
uv run autodiscover --root runtime market-source RUN_ID https://HOST/PATH --title 'Public source' --allow-network
uv run autodiscover --root runtime market-evidence OPPORTUNITY_ID evidence.json
uv run autodiscover --root runtime market-review EVIDENCE_ID review.json
uv run autodiscover --root runtime market-show OPPORTUNITY_ID
```

Public collection pins a public numeric address, verifies TLS hostname and enforces the existing redirect/time/body controls. The explicit URL and network flag authorize only that origin. Imported UTF-8 documents are bounded to 2 MB, stored under content addresses without their local path, and require separate review. Environment files and recognizable credential material are rejected. Private operator records remain in ignored runtime storage; do not archive them into Git.

Current acceptance demonstrates a real local technical experiment correctly classified as commercially unvalidated. Levels 1–4 are verified with clearly identified local contract fixtures, not real-world buyer or payment validation.
