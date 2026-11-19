# AI Website Link Analysis API

FastAPI service that fetches a public website, extracts readable page evidence, and asks an LLM to return structured business, competitor, search query, SEO, service, and audience analysis.

## Run locally

Requires Python 3.10 or newer and an API key for an OpenAI-compatible chat completions endpoint.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `LLM_API_KEY` in `.env` to your Google AI Studio API key, then start the server. The configuration is already set to Google's OpenAI-compatible endpoint and `gemini-3.8-flash`.

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Open interactive API docs at <http://localhost:4000/docs>. Health check: `GET /health`.

## Request

```http
POST http://localhost:4000/link-analysis
Content-Type: application/json
```

```json
{"url":"https://example.com"}
```

The response contains `success`, `website`, `brand`, and `analysis` with five sections: `competitor_analysis`, exactly five `target_search_queries`, `seo_improvements`, exactly five `top_services`, and `target_audience`. The service classification records whether each service was found on the website or inferred. Competitors are labeled `suggested` unless independently verified; this implementation does not perform competitor web research. Search volume and ranking metrics are never fabricated.

Invalid URLs and fetch/SSRF checks return HTTP 422. Missing LLM configuration returns 503; upstream LLM or malformed output returns 502. The API caches completed analyses in process memory for 15 minutes by default. Set `CACHE_TTL_SECONDS=0` to disable reuse. This cache is intentionally small/simple for a practical test; production should use a bounded shared cache with eviction and privacy controls.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `google-ai-studio` | Informational provider setting |
| `LLM_API_KEY` | empty | Google AI Studio API key; never commit `.env` |
| `LLM_MODEL` | `gemini-3.8-flash` | Model name |
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini OpenAI-compatible API base |
| `LLM_TIMEOUT_SECONDS` | `60` | LLM request timeout |
| `MAX_PAGE_BYTES` | `2000000` | Maximum HTML download size |
| `MAX_CONTENT_CHARS` | `18000` | Maximum extracted text sent for analysis |
| `CACHE_TTL_SECONDS` | `900` | In-memory cache lifetime |

The extractor blocks non-public IP addresses, resolves hostnames before every request, checks every redirect, limits response size, and accepts only HTML. As with any URL fetcher, production deployment should additionally use an egress firewall/network policy that denies private and metadata ranges to defend against DNS rebinding and infrastructure changes between validation and connection.

## LLM choice and cost notes

**Recommended default: OpenAI GPT-6 Luna.** It is positioned for efficient high-volume focused tasks, supports structured outputs, and has a 1.05M-token context window. For this workload the prompt is deliberately bounded to a small extracted page rather than using that large context. Current standard rates listed by OpenAI are $0.10 per million input tokens and $0.50 per million output tokens. At an estimated 8,000 input and 2,000 output tokens, a single analysis costs about **$0.0018 USD** (`0.008 × $0.10 + 0.002 × $0.50`). Token use and actual bill depend on the page, prompt/schema, output, provider tier, and retries. This is an estimate, not measured API usage or a quality benchmark.

| Provider/model | Input / output per 1M tokens | Context / JSON capability | Speed | Fit |
|---|---:|---|---|---|
| OpenAI GPT-6 Luna | $0.10 / $0.50 | 1.05M context; structured outputs supported | Provider positions it for efficient high-volume work; no app latency measured | Best default cost/structured-output balance for one-pass page analysis |
| Google Gemini 2.5 Flash | $0.30 / $2.50 | 1M context; JSON mode available | Flash family is speed-oriented; no app latency measured | Strong alternative when large-context handling or Google ecosystem is useful |
| Anthropic Claude Haiku 5.5 | $0.10 / $0.50 for prompts up to 100K | See current model docs for context and structured output/tooling details | Haiku is positioned for fast tasks; no app latency measured | Comparable low-cost fallback candidate; validate compatibility with this adapter before switching |

Pricing is standard text-token pricing, checked 19 November 2026. Rates, model names, quotas, and feature availability change; confirm before deployment. Sources: [OpenAI GPT-6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna), [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Anthropic Haiku](https://www.anthropic.com/claude/haiku).

No provider latency or general accuracy number is claimed here: those need representative workload measurements. Benchmark each candidate on a labeled set covering industries, short/long pages, multilingual content, and low-information pages. Track schema validity, factual grounding, business relevance, p50/p95 latency, and per-analysis token costs. Competitor identity/strength claims need external evidence sources; this implementation explicitly marks them as suggestions.

Cost controls implemented here include HTML cleanup, content length limits, one analysis call, and repeated-request caching. Additional production improvements: fetch relevant same-domain service/about pages with strict page and total-token limits, use a persistent bounded cache, cap response tokens if supported, and use a cheaper extraction model only when benchmarks show no quality loss. Do not use search volume estimates without a real keyword data provider.

## Notes and limitations

- Single-page extraction may miss dynamically rendered content, linked pages, and facts behind access controls.
- The LLM interprets supplied text; it does not independently validate claims or identify competitors from research sources.
- The cache is per-process and memory-only. Do not run multiple workers expecting shared caching.
- Keep API keys in environment variables or a secret manager. Never commit credentials.
- Before publishing, add rate limiting, observability, bounded cache eviction, and an egress firewall.
