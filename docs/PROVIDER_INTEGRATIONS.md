# Provider integration evidence — checked 2026-11-03

Official Meta [API reference](https://dev.meta.ai/docs/api-reference) documents `https://api.meta.ai/v1`, bearer auth and `/chat/completions`. The [chat schemas](https://dev.meta.ai/docs/api-reference/chat-completions/schemas) document completion token caps, structured response formats and token usage. The adapter uses `max_completion_tokens`, validates returned content/usage, and rejects truncated/refused output. Models and task-specific capabilities require explicit configuration; legacy Llama API is not assumed interchangeable.

Official Baseten [Model APIs overview](https://docs.baseten.co/inference/model-apis/overview) and [chat reference](https://docs.baseten.co/reference/inference-api/chat-completions) document the inference origin, bearer auth and compatible message/usage envelopes. This implementation targets Model APIs, not arbitrary custom deployments. It uses `max_tokens`; structured capability must be configured for the selected model.

No specific model, context window, price or rate limit is shipped as a live default. Model catalog health probes establish availability only. Provide current model/pricing/capability sources, verification date, environment variable name, and explicit authorization. Credentials are read only on authorized adapter use. HTTP tests inject mock transports and fake credentials. The dated qualification report records the separate live Meta results.

Reservations use a conservative estimate based on configured context and completion limits. The estimate supports accounting. It does not limit dispatch or invalidate an otherwise valid response when actual cost is higher. Ambiguous consumption keeps the reservation, including after a crash. Cost dates use UTC request day. Cached completed results avoid repeat calls; incomplete request identity needs explicit reconciliation. A failure may fall back only along a preconfigured route with a task-specific evaluation reference; selection identity and comparison evidence are persisted. No claim of model-family equivalence follows from a common HTTP shape.

## Hackathon profile and reasoning controls

Use the opt-in `ProviderConfig` settings below for the restricted Baseten key. Supply the verified price and context fields separately and keep `live_authorized=False` until the live gate clears. The key stays in the process environment. The existing `standard` profile continues to accept ordinary Baseten model configuration and credentials.

| Field | Hackathon setting |
| --- | --- |
| `kind` | `baseten` |
| `profile` | `baseten_hackathon` |
| `model` | `meta-models/muse-spark-open-1026` |
| `api_key_env` | `BASETEN_HACKATHON_API_KEY` |
| `structured_output` | `False` |
| `reasoning_effort` | Omit |

The supplied hackathon email controls the restricted model ID. The profile fixes the bearer request to `POST https://inference.baseten.co/v1/chat/completions` with `model`, `messages`, `stream: false`, and `max_tokens`. It refuses catalog probes. A structured task places its JSON schema in the prompt and validates final JSON locally. Support for native schema enforcement and `reasoning_effort: "low"` on the restricted ID is unconfirmed. Baseten documents always-on reasoning and the lower effort for the general Muse Spark Open model. [Quickstart](https://docs.baseten.co/quickstart), [chat completions](https://docs.baseten.co/reference/inference-api/chat-completions), [reasoning](https://docs.baseten.co/inference/model-apis/reasoning).

Direct Meta `muse-spark-1.3`, `muse-spark-1.2`, and `muse-wonder-1.0` can explicitly use top-level `reasoning_effort: "minimal"` or `"low"`. This integration accepts `"low"` for the general Baseten Muse Spark Open ID. Meta Chat Completions uses `max_completion_tokens`, which covers hidden reasoning and visible text together. Use strict native JSON Schema for the supported direct Meta models. The closed-root required-field repair from `fcf343e` still applies. The ResearchTeam asks for short responses and uses bounded public excerpts with the existing 512-token request cap. [Meta reasoning](https://dev.meta.ai/docs/reasoning), [Meta chat schema](https://dev.meta.ai/docs/api-reference/chat-completions/schemas), [Meta structured output](https://dev.meta.ai/docs/structured-output).

The adapter accepts final `message.content` from a successful stop and requires an explicit returned model. It rejects length stops, refusals, reasoning-only responses, empty content and malformed or invalid structured data. When present, `reasoning_tokens` is a subset of `completion_tokens`. Complete token usage attributed to the configured model can settle a failed output at configured rates without caching a result. Ledger settlement is a local calculation, and provider charges can differ. HTTP failures without usage and ambiguous transport outcomes retain the full reservation. See the [qualification report](phase_reports/hackathon-model-qualification.md) for the current live gate.
