# Replacing the Anthropic API with OpenRouter: plan and cost comparison

2026-09-26. A plan only: no code has been written. Prices come from OpenRouter's public model list (`GET https://openrouter.ai/api/v1/models`, fetched 2026-09-26, 458 models) and from Anthropic's price table. The token counts come from the usage EMA recorded in `evals/results/*.json`. Anything marked **(unverified)** comes from documentation or search results and has not been tried against the API.

## 1. Summary

- **Recommended route: keep the Anthropic SDK and point it at OpenRouter's Anthropic-compatible endpoint** (`POST https://openrouter.ai/api/v1/messages`, base URL `https://openrouter.ai/api`, bearer auth). The Tool Runner, the 28 `@beta_tool` tools, streaming, the replay cassettes, grounding, and traces keep their Anthropic shape. The change is confined to the client, the model tables, the price table, and the secrets. Rewriting against OpenAI-style chat completions (route B, §4) is the fallback. Use it only if the Messages endpoint turns out to translate the chosen non-Anthropic model badly.
- **Run the Claude models through OpenRouter first, then the others.** Claude models cost the same on OpenRouter as direct: OpenRouter "pass[es] through the pricing of the underlying providers without any markup". The only extra is a **5.5% fee on credit purchases by card** ($0.80 minimum; 5% by crypto). With bring-your-own-key (BYOK), the first $25,000 a month is fee-free. So step 1 costs about 5.5% more and changes nothing else, which makes it a clean test of the new plumbing. Step 2 screens cheaper models against the evals.
- **The price spread is large; the quality spread is unknown.** On EMA's measured token profile, the cheapest plausible models cost 3–25% of Haiku 4.5, and Opus 5 costs 5×. None of the non-Anthropic models have been run through EMA's evals. CLAUDE.md requires any change of default model to pass the reliability gate, so the gate decides, not the price list.

## 2. What EMA depends on today

Survey of the code, with references:

| Area | Dependency | Where |
|---|---|---|
| Loop | `client.beta.messages.tool_runner(...)` streaming; reads `text` and `content_block_start`/`tool_use` events; `get_final_message()`; `generate_tool_call_response()` | `agent/session.py:299-345` |
| Request | `model`, `max_tokens=64000`, `system`, `tools`, thinking options, top-level `cache_control={"type":"ephemeral"}`, `stream=True`; with fallbacks, `betas=["server-side-fallback-2026-07-01"]` and `fallbacks="default"` | `session.py:211-224` |
| Stop reasons | tools run only on `tool_use`; `STOP_NOTICES` for `refusal`, `max_tokens`, `model_context_window_exceeded`; cut-off tool calls get synthetic error results | `session.py:30-34, 361-384` |
| History | Anthropic Messages shape; raw SDK blocks kept for assistant turns (thinking blocks passed back unchanged) | `session.py:342` |
| Tools | 28 `@beta_tool`, `ToolError`, `BetaFunctionTool.call/.name/.description/.to_dict()`; `view_figure` returns Anthropic image blocks | `agent/tools/*`, `_common.py:193-218`, `inspection.py:84` |
| Models | `MODEL="claude-haiku-4-5"`; `ADAPTIVE_THINKING_MODELS`, `BUDGET_THINKING_MODELS` (`THINKING_BUDGET=8000`), `EFFORT_LEVELS`; unknown ids raise `ValueError` | `agent/config.py` |
| Cost | price table `(input, output, cache read)` $/MTok, cache write = 1.25 × input; `CostCap` (`--max-cost`), `--estimate`; `cost_usd` read by the gate and reliability | `evals/runner.py:184-226, 386-406, 600-663` |
| Second call site | confidence question: `client.beta.messages.stream(..., tool_choice={"type":"none"})` | `evals/runner.py:350` |
| Replay | cassettes are Anthropic SSE (`message_start`, `content_block_*`, `thinking_delta`, `signature_delta`, ...) served to a real `anthropic.Anthropic` over `httpx2`; about 52 of 688 test functions use it | `agent/replay.py` |
| Trace, grounding | four Anthropic usage keys; fallback detected by the `model` field; grounding parses `tool_use`, `tool_result`, `text`, `image` | `agent/trace.py`, `agent/grounding.py` |
| Secrets | SDK reads `ANTHROPIC_API_KEY`; `WITHHELD_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")`; `.config/anthropic` on the deny list; CI secret in `ci.yml:72`, `agent-evals.yml:31` | `core/models/_sandbox.py:48`, `agent/approval.py:66` |
| Provenance | records the `anthropic` version | `core/provenance.py:29` |
| CLI | `--model`, `--effort`, `--no-thinking`, `--no-fallbacks`, `--record`; `ema list` must not import the SDK | `cli.py:750-936` |

## 3. Route A (recommended): the Anthropic SDK against OpenRouter's Messages endpoint

According to OpenRouter's documentation **(unverified)**, `/api/v1/messages` accepts:

- the Anthropic request fields: `thinking` (enabled, disabled, or adaptive, with `budget_tokens` and `display`), `tools`, `tool_choice`, `stream`, top-level and per-block `cache_control` (5 min or 1 h), `system`, and `output_config.effort` and `format`;
- the Anthropic content blocks, including `thinking` with `signature` and `redacted_thinking`;
- the Anthropic `usage` keys, plus OpenRouter's own `cost`, `cost_details`, `is_byok`, and `iterations`;
- OpenRouter extensions: `provider` routing (`order`, `only`, `ignore`, `allow_fallbacks`, `data_collection`, `zdr`, `max_price`), `models`/`fallbacks` (at most 3), `session_id`, and `trace`.

The documented `stop_reason` values are `end_turn`, `stop_sequence`, `tool_use`, and `max_tokens`. `stop_details` is present, but `refusal` is not listed.

For non-Anthropic models, OpenRouter's Claude Code guide warns that the Anthropic interface "may not work correctly with other providers". One report says `/messages` accepted `qwen/qwen3.7-flash`, `deepseek/deepseek-v4.1-flash`, and `openai/gpt-5.6-luna`. How `thinking` and `effort` map onto those models is not documented.

### What changes

1. **Client construction** (`session.py:178`, `cli.py:767`, `evals/runner.py`). A provider setting (`anthropic` | `openrouter`, from `EMA_LLM_PROVIDER` or a `--provider` flag) chooses the base URL and credential. For OpenRouter, it passes the key as an auth token (bearer), not as `x-api-key`. The Tool Runner posts to `/v1/messages?beta=true`; confirm that OpenRouter accepts the `beta` query and ignores or rejects `anthropic-beta` headers **(unverified)**.
2. **Model tables** (`agent/config.py`). OpenRouter ids are `vendor/model` with dots (`anthropic/claude-haiku-4.5`, not `claude-haiku-4-5`). Add a table of OpenRouter models, each with its thinking style (`adaptive`, `budget`, or `none`), its effort levels, and whether it takes `cache_control`. `thinking_options` keeps refusing an id it doesn't know, before the first request (a design rule).
3. **Refusal fallbacks.** `fallbacks="default"` is an Anthropic server-side feature and the beta header is Anthropic's. Under OpenRouter, either drop it (`--no-fallbacks` behaviour; Haiku 4.5 rarely refuses) or map it to OpenRouter's `models` list. `trace.py`'s fallback detection by `model` still works, since OpenRouter returns the model that served the request.
4. **Provider pinning and data policy.** Every request sends `provider: {data_collection: "deny", allow_fallbacks: false}`, plus `order`/`only` for open-weight models. Open-weight models are served by several hosts with different prices, quantization, and caching. Without pinning, two runs of the same eval can hit different hosts, which the reliability metrics would count as inconsistency. EMA sends model specs, run results, and files the agent reads. Some users' simulators are proprietary, so data collection is off by default and `zdr: true` is available as an option.
5. **Cost** (`evals/runner.py`). Record OpenRouter's billed `usage.cost` in `cost_usd` when present. Keep the price table for `--estimate` and as the fallback, keyed by OpenRouter id. Add the credit fee (5.5% by default) as a named constant that `--estimate` and `--max-cost` apply, so the cap stays conservative. Cache-write pricing is not always 1.25× (Gemini and DeepSeek have no write premium; OpenAI's GPT-5.6+ charges 1.25×), so the table needs a fourth column.
6. **Caching.** Keep top-level `cache_control` for Anthropic models, as OpenRouter supports it. For OpenAI, DeepSeek, Gemini, Grok, Moonshot, and Z.ai, caching is automatic. Check that a cache hit shows up in `cache_read_input_tokens` on the Messages endpoint **(unverified: the chat-completions API reports it as `prompt_tokens_details.cached_tokens`)**. Nearly all of EMA's input is cached (all but about 30 of the 55K input tokens in a repeat), so a model whose cache isn't used costs 2–3× its cached price (§5, the "no cache" column).
7. **Secrets.** Add `OPENROUTER_API_KEY` to `WITHHELD_ENV` and to its tests (`test_isolation.py`, `test_cli_model.py`, `test_agent.py`, `test_approval.py`). Add it to the missing-key hint in `cli.py:769` and to `evals/scenarios.py:264`. The key lives in `.env` like the Anthropic one (never read or printed).
8. **Provenance and traces.** Record the provider, the routed model, and OpenRouter's endpoint and host (`X-OpenRouter-Metadata: enabled` returns `openrouter_metadata`), so that a campaign's findings record which host produced them.
9. **Replay and tests.** The cassette format stays Anthropic SSE, so the 52 replay tests are untouched. Add offline tests for:
   - the base URL and bearer header;
   - reading `usage.cost`;
   - the provider block being sent;
   - an OpenRouter error body (its JSON differs from Anthropic's; `session.py:485-495` parses `body["error"]["type"]`);
   - `thinking_options` for each OpenRouter family.
10. **CI and docs.** Add the `OPENROUTER_API_KEY` secret to `agent-evals.yml` and `ci.yml`; you add the secret, and nothing triggers the workflow. Update the key instructions in `README.md:47`, `docs/index.md:24`, and `docs/tutorials/index.md:25`. Add a "Choosing a provider" section to `docs/guides/agent_evals.md`. Recorded tutorial transcripts stay as recorded (they name their model).

### What you lose, or must replace

- Anthropic's server-side refusal fallbacks, `ant auth login` profiles, and Anthropic `request-id`s for support (OpenRouter has its own generation ids).
- Any future Anthropic beta that OpenRouter hasn't adopted (for example mid-conversation system messages, which EMA doesn't use today).
- For non-Anthropic models, the Anthropic-specific prompting in `prompts.py` and the tool docstrings may need retuning. That is a gated change under CLAUDE.md.

## 4. Route B (fallback): OpenAI-compatible chat completions

Use this only if route A mistranslates the chosen model (its tool calls, reasoning continuity, or caching). It means:

- Replace the Tool Runner with EMA's own loop over `/api/v1/chat/completions`.
- Convert each `BetaFunctionTool.to_dict()` schema to a `{"type":"function"}` tool.
- Store history as `role: tool` messages, and pass reasoning back as `reasoning_details`, which must be echoed unchanged and in order across tool turns.
- Parse `finish_reason` (`tool_calls`, `length`, `content_filter`, `stop`) into EMA's stop handling.
- Map image blocks for `view_figure`.
- Read usage from `prompt_tokens_details.cached_tokens` and `cache_write_tokens`.
- Rewrite `replay.py` to serve chat-completion SSE. About 52 tests depend on it, so both formats would have to live behind a provider interface for a while.
- Update grounding and trace parsing for the new shapes.

This is several times the work of route A and touches every harness rule in CLAUDE.md's agent section (cut-off tool calls, `repair_after_api_error`, revise mode). Put a `Provider` interface in `agent/` first, so that route A and route B are two implementations and the Anthropic path stays available.

## 5. Cost comparison

### Method

Each model's OpenRouter price, applied to token profiles EMA has measured on Haiku 4.5:

- **Eval repeat** (the default setup: thinking, revise mode; 3,175 repeats in 42 results files). Per repeat: 4.4 requests, 31 uncached input tokens, 14,927 cache-write, 40,236 cache-read, and 1,343 output tokens, **$0.0294** on Haiku direct.
- **Long session** (phase-6 truth-paraphrase repeats: several analyst turns, diagnostics run, findings recorded). Per repeat: 71 / 39,090 / 141,185 / 4,984 tokens, **$0.088** on Haiku direct. This is closer to a real `ema chat` session.
- **Gate run** (`agent-evals.yml`, base plus paraphrase at K = 5): **$15.16** measured on Haiku. Scaled by each model's ratio to Haiku.

Every OpenRouter figure includes the 5.5% credit fee. Cache writes are billed at the listed cache-write price, or at the input price where there is none (automatic caching); Gemini's are billed at the input price.

### Per-repeat and per-run cost (USD, including the 5.5% fee)

| Model (OpenRouter id) | $/M in | $/M out | Eval repeat | ×3 output | No cache | Long session | Gate run | × Haiku (before fee) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Anthropic direct: claude-haiku-4-5** (today) | 1.00 | 5.00 | 0.0294 | 0.0429 | 0.0619 | 0.088 | 15.16 | 1.00 |
| Anthropic direct: claude-sonnet-5 | 2.00 | 10.00 | 0.0589 | 0.0857 | 0.1238 | 0.176 | 30.32 | 2.00 |
| Anthropic direct: claude-opus-5.5 | 4.00 | 20.00 | 0.1097 | 0.1634 | 0.2476 | 0.324 | 56.5 | 3.73 |
| Anthropic direct: claude-opus-5 | 5.00 | 25.00 | 0.1471 | 0.2143 | 0.3095 | 0.440 | 75.8 | 5.00 |
| anthropic/claude-haiku-4.5 | 1.00 | 5.00 | 0.0310 | 0.0452 | 0.0653 | 0.093 | 15.99 | 1.00 |
| anthropic/claude-sonnet-5 | 2.00 | 10.00 | 0.0621 | 0.0904 | 0.1306 | 0.186 | 31.99 | 2.00 |
| anthropic/claude-opus-5.5 | 4.00 | 20.00 | 0.1157 | 0.1724 | 0.2613 | 0.341 | 59.60 | 3.73 |
| anthropic/claude-opus-5 | 5.00 | 25.00 | 0.1552 | 0.2261 | 0.3266 | 0.464 | 79.97 | 5.00 |
| openai/gpt-6-luna | 0.10 | 0.50 | 0.0031 | 0.0045 | 0.0065 | 0.009 | 1.60 | 0.10 |
| openai/gpt-5.6-luna | 0.20 | 1.20 | 0.0065 | 0.0099 | 0.0133 | 0.020 | 3.34 | 0.21 |
| openai/gpt-5.4-mini | 0.75 | 4.50 | 0.0214 | 0.0341 | 0.0500 | 0.066 | 11.02 | 0.69 |
| openai/gpt-6-sol | 2.00 | 10.00 | 0.0621 | 0.0904 | 0.1306 | 0.186 | 31.99 | 2.00 |
| google/gemini-3.1-flash-lite | 0.25 | 1.50 | 0.0071 | 0.0114 | 0.0167 | 0.022 | 3.67 | 0.23 |
| google/gemini-3.8-flash | 0.75 | 3.75 | 0.0203 | 0.0310 | 0.0490 | 0.062 | 10.47 | 0.65 |
| google/gemini-3.1-pro-preview | 2.00 | 12.00 | 0.0571 | 0.0911 | 0.1335 | 0.176 | 29.39 | 1.84 |
| deepseek/deepseek-v4.1-flash | 0.035 | 0.29 | 0.0010 | 0.0018 | 0.0024 | 0.003 | 0.52 | 0.03 |
| deepseek/deepseek-v4-pro | 0.348 | 0.70 | 0.0077 | 0.0097 | 0.0213 | 0.022 | 3.97 | 0.25 |
| qwen/qwen3.7-plus | 0.32 | 1.28 | 0.0108 | 0.0145 | 0.0204 | 0.033 | 5.58 | 0.35 |
| z-ai/glm-5.3 | 0.238 | 0.75 | 0.0065 | 0.0086 | 0.0149 | 0.020 | 3.34 | 0.21 |
| minimax/minimax-m3 | 0.30 | 1.20 | 0.0090 | 0.0124 | 0.0192 | 0.028 | 4.63 | 0.29 |
| moonshotai/kimi-k2.6 | 0.95 | 4.00 | 0.0275 | 0.0388 | 0.0610 | 0.084 | 14.14 | 0.88 |
| x-ai/grok-4.7 | 1.60 | 4.80 | 0.0490 | 0.0626 | 0.1000 | 0.151 | 25.26 | 1.58 |

Cache-read prices ($/M), for reference: Haiku 0.10, Sonnet 5 0.20, Opus 5.5 0.20, Opus 5 0.50, GPT-6 Luna 0.01, GPT-5.6 Luna 0.02, Gemini 3.8 Flash 0.075, DeepSeek V4 Pro 0.029, GLM-5.3 0.039, Qwen 3.7 Plus 0.064, Kimi K2.6 0.16, Grok 4.7 0.40. Mistral Medium 3.5 ($1.50/$7.50) lists no cache price, which puts it at about 3.2× Haiku on this profile. Batch (`:batch`) variants are half price, but they don't fit an interactive agent.

### How to read it

- **The Claude models cost 5.5% more through OpenRouter, for nothing gained in price.** With BYOK, which attaches your own Anthropic key, it is 0% up to $25,000 a month. You still need an Anthropic account, though, which removes much of the point. The reasons to route Claude through OpenRouter are one bill and one key across vendors, and the option to switch models by id.
- **For the Opus 5 and Sonnet 5 settings in `docs/guides/agent_evals.md`, the matching price points are GPT-6 Sol and Gemini 3.1 Pro (about 2× Haiku).** The cheapest tier (GPT-6 Luna, DeepSeek V4.1 Flash) is 3–10% of Haiku. At those prices, a gate run costs under $2 and a long session well under a cent. Revise mode could then be kept on, and more repeats run, for the same money.
- **Output-heavy models change the picture less than you'd think.** Cached input dominates EMA's bill: on Haiku, output is about 23% of the cost per repeat. Tripling the output (a more verbose reasoner) raises the cost 25–60%, not 3×.
- **A broken cache is the bigger risk:** the "no cache" column is 2–3× the cached one. Pinning a host that caches, and checking `cache_read_input_tokens` after the first requests, matters more than the list price.

### What the table can't tell you

- **Tokenizers differ.** The same prompt can be ±20–35% as many tokens on another model family. Real counts come from the first screening run.
- **Turns differ.** A weaker model may need more requests, trigger more revisions (each revise adds a request), or fail scenarios. **Cost per passing repeat** is the number that matters, and `evals.reliability` can report it once runs exist.
- **Open-weight prices are per host.** The list shows OpenRouter's listed endpoint. Pinning a host for quality or data policy can cost more. Prices change often, so re-fetch `/api/v1/models` before deciding.
- **Quality is unmeasured.** Nothing in this table says any model passes EMA's 27 scenarios. For comparison, Haiku 4.5 with revise mode passed 39 of 39 repeats in the model comparison, and every Opus 5 and Sonnet 5 setting passed 13 of 13 scenarios.

## 6. Phases, each with a stop condition

Each phase is a branch (`or-N-<topic>` from `main`), reviewed before the next. Live runs cost money and happen only when you ask. Estimated live spend is given per phase.

### Phase 0: Check the endpoint by hand (about $0.10)

Confirm the **(unverified)** points before any code:

- the Tool Runner against `/api/v1/messages` with bearer auth;
- `cache_control` producing `cache_read_input_tokens` on the second request;
- Haiku's `budget_tokens` thinking and signed thinking blocks surviving a tool turn;
- how `anthropic-beta` headers are treated;
- the shape of the error body;
- `usage.cost`.

Then do the same for one non-Anthropic model (for example `deepseek/deepseek-v4-pro`).

**Stop if** the Tool Runner or thinking-block continuity fails for Claude models: route A is then off, so replan around route B.

> **Prompt:** "Read docs/brainstorms/openrouter_migration.md §3 and §6 Phase 0. Don't change any EMA code. Write a throwaway script in $CLAUDE_JOB_DIR/tmp that uses the installed `anthropic` SDK with base_url https://openrouter.ai/api and OPENROUTER_API_KEY as an auth token (don't read or print .env; ask me to export the key). Using a two-tool toy (the Tool Runner with @beta_tool), check, for anthropic/claude-haiku-4.5 and then deepseek/deepseek-v4-pro:
> - streaming;
> - tool calls;
> - thinking blocks passed back across a tool turn;
> - cache_read_input_tokens on a repeated prefix;
> - usage.cost;
> - an error body (bad model id);
> - what happens with betas=[...].
>
> Keep each check under 2,000 output tokens and report a table of pass or fail with the raw evidence. Ask before running."

### Phase 1: Provider switch, Claude models only (gate run about $16)

- Implement §3 items 1–10 for Anthropic models under OpenRouter, with Anthropic direct still the default.
- Add offline tests (replay plus the new header, cost, and provider tests).
- Run the full suite, the doctests, ruff, and the docs build.
- Then run the gate: Haiku through OpenRouter against `evals/reference.json`, with `python -m evals.gate evals/reference.json AFTER --paraphrase P`.

**Stop if** the gate fails or is incomplete. The model is the same, so any difference is a plumbing bug.

> **Prompt:** "Implement Phase 1 of docs/brainstorms/openrouter_migration.md on a new branch or-1-provider from main: a provider setting (anthropic | openrouter), a bearer client for OpenRouter, OpenRouter ids for the Claude models in agent/config.py, provider pinning with data_collection deny, billed usage.cost in evals/runner.py with the credit fee as a named constant, OPENROUTER_API_KEY in WITHHELD_ENV and its tests, and provenance of the provider and routed model. Keep Anthropic direct the default and the replay format unchanged. Add offline tests for each change. Run the full test suite, doctests, ruff, and the -W docs build, and report. Don't run live evals; tell me the exact gate command to run."

### Phase 2: Screening candidates (about $5–10 in all)

Add thinking and effort rows for about six candidates spanning vendors and price tiers:

- `openai/gpt-5.6-luna` or `gpt-6-luna`
- `google/gemini-3.8-flash`
- `deepseek/deepseek-v4-pro`
- `z-ai/glm-5.3`
- `qwen/qwen3.7-plus`
- `moonshotai/kimi-k2.6`

Keep Haiku through OpenRouter as the control. For each, run `python -m evals.runner --variant base --repeats 3 --max-cost 3 --keep DIR`, then `evals.reliability --per-scenario` and `evals.safety`. Classify every failure, safety event, and wrong-scored finding before comparing them (as the reliability plan requires). Compare pass rate, pass^k, cost per passing repeat, and grounding.

**Stop and replan** if no candidate gets within the paired-bootstrap interval of the control. Also stop and replan, towards route B for that model, if failures trace to the Messages translation (tool calls written as text, lost reasoning, no cache hits) rather than to the model.

> **Prompt:** "Using Phase 1's provider switch, add rows to agent/config.py for the candidates listed in docs/brainstorms/openrouter_migration.md §6 Phase 2, each with its thinking style, effort levels, and pinned host (check each model's endpoints at https://openrouter.ai/api/v1/models/<id>/endpoints and prefer hosts with data_collection deny and caching). Then give me, without running them, the evals.runner commands for a base-variant screen at K = 3 with --max-cost per model and --keep, and an --estimate for each from evals/reference.json. After I run them, classify every failure (model vs translation vs harness) from the kept transcripts before any comparison."

### Phase 3: Choose and gate (about $2–35, depending on the model)

Take the best one or two candidates through the full gate (base plus paraphrase at K = 5) against the reference. Look at the failures that are specific to the model. Any retuning of `prompts.py` or tool docstrings is its own gated change.

**Stop if** the gate fails. Keep Haiku (direct or through OpenRouter) as the default and record the candidate's results in `docs/guides/agent_evals.md`.

### Phase 4: Switch the default and document it

- Change `MODEL` (or the provider default), `README.md`, `docs/index.md`, the tutorials' setup, and `agent_evals.md`'s model table.
- Record the committed reference for the new default with `--make-reference`.
- Keep Anthropic direct selectable.
- Write a memory entry and update CLAUDE.md's Commands and Design rules (a new design rule: "providers are pinned and data collection is off").

### Route B, only if needed

Put the `Provider` interface in first (Anthropic implementation unchanged, all tests green), then add the chat-completions implementation with its own replay format. That is a separate plan; don't start it unless Phase 0 or Phase 2 calls for it.

## 7. Risks and open questions

- **The Messages translation for non-Anthropic models is undocumented.** It is the main technical risk, and Phase 0 exists to measure it.
- **Reproducibility.** Routed open-weight models can change host or quantization. Pin hosts, record the routed endpoint, and treat an unpinned run as not comparable.
- **Data.** EMA sends model descriptions and results to whichever vendor serves the request. Choose whether `zdr: true` should be the default for analysts with proprietary models.
- **Rate limits and outages** now involve two services. `MAX_RETRIES` and `is_transient` need OpenRouter's 429 and 5xx semantics **(unverified)**.
- **Cost figures** assume the Haiku token profile; §5 lists what changes them. Re-fetch prices before each decision.
- **Decision for you:** whether the goal is lower cost (then Phase 2 and 3 matter), vendor independence (then Phase 1 alone may be enough), or both.

## Sources

- OpenRouter models and prices: `https://openrouter.ai/api/v1/models` (fetched 2026-09-26)
- OpenRouter fees ("5.5% ($0.80 minimum)", BYOK $25,000 a month then 5%, "no markup on inference pricing"): [FAQ](https://openrouter.ai/docs/faq)
- Anthropic-compatible endpoint: [Create a message](https://openrouter.ai/docs/api/api-reference/anthropic-messages/create-a-message), [Claude Code integration](https://openrouter.ai/docs/guides/guides/claude-code-integration), [Claude Code with OpenRouter](https://openrouter.ai/blog/tutorials/claude-code-openrouter/)
- Caching: [Prompt caching](https://openrouter.ai/docs/features/prompt-caching)
- Reasoning and `reasoning_details` continuity: [Reasoning tokens](https://openrouter.ai/docs/use-cases/reasoning-tokens)
- Report of non-Anthropic models on `/messages`: [system-one-router PR #7](https://github.com/mmornati/system-one-router/pull/7)
- Anthropic prices: the claude-api skill's model table (cached 2026-06-24), which matches the `anthropic/*` rows of OpenRouter's list
- EMA token profiles: `evals/results/*.json` (usage per repeat); gate cost: `docs/guides/agent_evals.md:853-858`

## 8. Addendum: what EMA's development has cost, and what it would have cost through OpenRouter

Added 2026-09-26. This section covers the API calls EMA itself made to Claude while it was being built: live evals, and live `ema chat` sessions. It does not cover Claude Code's own usage in building EMA, which is billed separately.

### Where the numbers come from

- **Session traces.** Every live `ema chat` session, including each eval repeat, writes `sessions/<id>.trace.jsonl`, with one `request` record per API call: its request id, the model that served it, and the full `usage`. I read every trace on disk outside pytest's temporary folders: 4,414 files, almost all in `evals/results/*/…/ws/sessions/`, plus `ema_workspace/` and a few Claude Code job folders. Deduplicated by request id (about 330 files were copies, such as `p3_*_merged` and `wave1b`), that leaves **16,564 API requests in 4,081 sessions, from 2026-09-23 01:38 to 2026-09-27 01:48 UTC**.
- **Checked against the results files.** The 116 results files in `evals/results/` record `cost_usd` for each repeat. For the 3,804 repeats that have both a results entry and a trace, the results record **$162.88** and pricing the traces gives **$162.49**. The $0.39 gap is probably the `--confidence` calls, which aren't traced. The 263 repeats with no trace are the `r2-*` run cut short by the usage limit, which recorded $0. The 277 traced sessions with no results entry ($22.55) are repeats whose results file was replaced or never written (for example `phase3_20260923`), and live `ema chat` sessions.
- **Prices.** Anthropic's list prices: cache writes at 1.25× input (every recorded write was a 5-minute write), cache reads at 0.1× input.

### What wasn't recorded

- **Sessions before tracing existed.** Tracing arrived on 2026-09-22 17:39 (commit `f0bd705`), a day after the first commit. The tutorial transcripts were recorded with Claude Opus 5 on 2026-09-22 (`docs/tutorials/index.md`), some of them twice. They and any other live session from that first day left no usage record. Assuming about 5–10 Opus sessions of 15–30 requests each, a guess is **$5–20**. It is not included in the totals below.
- **CI.** The Agent evals workflow has never run on GitHub (`gh run list`), and the one manual CI run (2026-09-24) skipped its live test (4 skipped).
- **Live pytest runs.** `tests/test_agent.py -k live` writes traces to pytest's temporary folders. The three that remain contain only offline replay traces (fake request ids), and older ones have been cleaned up.

### Actual cost: $185.05, at Anthropic's prices

Totals by model:

| Model | Requests | Uncached input | Cache write | Cache read | Output | Cost |
|---|---:|---:|---:|---:|---:|---:|
| claude-haiku-4-5 | 13,168 | 91,063 | 45,360,301 | 117,122,008 | 3,999,733 | $88.50 |
| claude-opus-5 | 2,350 | 4,700 | 8,374,505 | 20,220,948 | 744,041 | $81.08 |
| claude-sonnet-5 | 1,046 | 2,092 | 4,496,011 | 8,050,122 | 261,532 | $15.47 |
| **Total** | **16,564** | **97,855** | **58,230,817** | **145,393,078** | **5,005,306** | **$185.05** |

By activity:

| Activity | Requests | Cost | Models |
|---|---:|---:|---|
| Model and effort comparison (`matrix*`, `wave1*`; 2026-09-23) | 4,259 | $85.42 | Opus 5 $61.86, Sonnet 5 $15.47, Haiku $8.09 |
| Reliability evals and gates (`p3`–`p6`, `s5`, `rule*`, `exp5`, `ctl`) | 11,707 | $80.15 | Haiku only |
| Harness-change evals before the comparison (`phase2`, `phase3`, `totals`) | 559 | $19.22 | Opus 5 only |
| Live `ema chat` sessions outside evals | 39 | $0.26 | Haiku |

By UTC day: 09-23 $104.64, 09-24 $22.04, 09-25 $52.14, 09-26 $3.15, 09-27 (the evening of 09-26 local time) $3.08.

Three things stand out:
- Nearly half the spend (46%) was the one-off model comparison, and Opus 5 alone was 44% of the total.
- The recurring cost is the Haiku reliability evals, about $80 over three days.
- Nearly all of the input was cached: 203.6M of 203.7M input tokens were cache writes or reads. **Cache writes were the largest cost, about $120 (65%)**, against $41 for output (22%) and $23 for cache reads (13%). Every eval repeat is a new session that writes its own cache of about 10–15K tokens (the system prompt, the tools, and the first turns). That makes the price of cache writes the figure to compare between providers: DeepSeek and Gemini charge no premium for them, and OpenAI's newer models charge 1.25×.

### What the same calls would have cost through OpenRouter

The same token counts, priced at each model's OpenRouter rates (fetched 2026-09-26) plus the 5.5% credit fee:

- **"All calls"** puts every one of the 16,564 requests on that model.
- **"Haiku's calls"** reprices only the 13,168 Haiku requests, whose actual cost was $88.50.
- **"Opus and Sonnet calls"** reprices only the 3,396 Opus 5 and Sonnet 5 requests, whose actual cost was $96.55.
- The last two columns are the sensitivities from §5 (three times the output; no cache hits).

| Model | All calls | Haiku's calls | Opus and Sonnet calls | All, ×3 output | All, no cache |
|---|---:|---:|---:|---:|---:|
| *Actual (Anthropic direct, mixed models)* | *185.05* | *88.50* | *96.55* | | |
| anthropic/claude-haiku-4.5 | 118.64 | 93.37 | 25.27 | 171.44 | 241.33 |
| anthropic/claude-sonnet-5 | 237.27 | 186.74 | 50.53 | 342.89 | 482.66 |
| anthropic/claude-opus-5.5 | 443.87 | 348.77 | 95.10 | 655.09 | 965.32 |
| anthropic/claude-opus-5 | 593.19 | 466.85 | 126.34 | 857.22 | 1,206.65 |
| openai/gpt-6-sol | 237.27 | 186.74 | 50.53 | 342.89 | 482.66 |
| google/gemini-3.1-pro-preview | 217.12 | 171.25 | 45.87 | 343.85 | 493.22 |
| qwen/qwen3.8-max-0902 | 223.82 | 176.04 | 47.78 | 287.19 | 461.54 |
| moonshotai/kimi-k3 | 309.84 | 244.22 | 65.62 | 468.25 | 723.99 |
| mistralai/mistral-medium-3-5 | 361.99 | 288.92 | 73.07 | 441.20 | 361.99 |
| x-ai/grok-4.7 | 185.16 | 146.40 | 38.76 | 235.86 | 369.23 |
| moonshotai/kimi-k2.6 | 104.12 | 82.20 | 21.92 | 146.37 | 225.30 |
| openai/gpt-5.4-mini | 81.42 | 64.22 | 17.20 | 128.94 | 184.96 |
| google/gemini-3.8-flash | 77.46 | 61.05 | 16.40 | 117.06 | 181.00 |
| qwen/qwen3.7-plus | 41.18 | 32.48 | 8.70 | 54.70 | 75.54 |
| minimax/minimax-m3 | 34.00 | 26.86 | 7.14 | 46.67 | 70.81 |
| deepseek/deepseek-v4-pro | 29.54 | 23.21 | 6.33 | 36.89 | 78.47 |
| google/gemini-3.1-flash-lite | 27.14 | 21.41 | 5.73 | 42.98 | 61.65 |
| openai/gpt-5.6-luna | 24.78 | 19.52 | 5.27 | 37.46 | 49.32 |
| z-ai/glm-5.3 | 24.59 | 19.40 | 5.19 | 32.49 | 55.10 |
| openai/gpt-6-luna | 11.86 | 9.34 | 2.53 | 17.14 | 24.13 |
| deepseek/deepseek-v4.1-flash | 3.84 | 3.03 | 0.81 | 6.90 | 9.05 |

The same development with the same roles, choosing an OpenRouter model for the cheap tier (in place of Haiku) and one for the strong tier (in place of Opus 5 and Sonnet 5):

| Scenario | Cheap tier | Strong tier | Total | vs actual |
|---|---|---:|---:|---:|
| Actual | Haiku 4.5, direct ($88.50) | Opus 5 and Sonnet 5, direct ($96.55) | $185.05 | 1.00 |
| Same Claude models through OpenRouter | Haiku 4.5 ($93.37) | Opus 5 and Sonnet 5 ($101.86) | $195.23 | 1.055 |
| OpenAI | GPT-5.6 Luna ($19.52) | GPT-6 Sol ($50.53) | $70.05 | 0.38 |
| Google | Gemini 3.8 Flash ($61.05) | Gemini 3.1 Pro ($45.87) | $106.92 | 0.58 |
| Open-weight and OpenAI | DeepSeek V4 Pro ($23.21) | GPT-6 Sol ($50.53) | $73.74 | 0.40 |
| Open-weight | GLM-5.3 ($19.40) | Qwen 3.8 Max ($47.78) | $67.18 | 0.36 |
| Cheapest plausible | GPT-6 Luna ($9.34) | DeepSeek V4 Pro ($6.33) | $15.67 | 0.08 |

### How to read it

- **At OpenRouter's list prices, the recorded development would have cost $4–$600, against $185 actual.** The low end puts everything on the cheapest tier, where a gate run costs under $2. The high end puts everything on Opus 5. Keeping the same two tiers with non-Anthropic models gives $67–107, about 0.36–0.58× of actual. Keeping Claude but going through OpenRouter adds the 5.5% fee ($10.18).
- **The biggest single saving would have come from the model comparison.** Its Opus 5 and Sonnet 5 calls cost $77 of the $185. On the same tokens, the strong-tier alternatives (Grok 4.7, Gemini 3.1 Pro, Qwen 3.8 Max, GPT-6 Sol, Kimi K3) cost $39–66 for all 3,396 Opus and Sonnet calls, and the cheap tier costs under $10.
- **This is a price comparison, not a counterfactual history.** It assumes the other models would have used the same tokens, made the same number of requests, and needed the same rounds of evals. In practice:
  - tokenizers differ by about ±20–35%;
  - more verbose reasoning raises the cost (the ×3 output column adds 25–60%);
  - a model whose cache isn't used costs 2–2.7× (the no-cache column);
  - a weaker model would have failed more scenarios and triggered more revisions, and development would have taken more gate rounds.

  The reliability evals were most of the Haiku spend. They were run to show that Haiku with revise mode was good enough, and a cheaper model would have had to show the same. The measurement in §6 Phase 2 (cost per passing repeat) is what turns these into a real comparison.
- **For future development, the recurring cost is the gate.** On Haiku it costs $15–20 per change to the agent (§5). On the candidate models in §6 Phase 2 it would cost $3–14, if they pass it.

### How to reproduce it

The throwaway scripts were in this job's temporary folder and are gone with it. To reproduce the figures:

1. List every `*.trace.jsonl` outside pytest's temporary folders.
2. Keep the records with `type == "request"`, deduplicated by `request_id`.
3. Sum `usage.input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, and `output_tokens` for each model family.
4. Price them at 1.25× input for writes and 0.1× input for reads, and at OpenRouter's `pricing.prompt`, `completion`, `input_cache_read`, and `input_cache_write` from `/api/v1/models` (per token; Gemini's writes at the input price).
5. Check the result against the sum of `usage.cost_usd` over the results files, deduplicated by `session_id`.

If this cost accounting will recur, it could become an `evals` command (for example `python -m evals.spend`).
