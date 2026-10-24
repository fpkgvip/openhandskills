# Brave Web Search reference (checked 2026-10-25)

Endpoint: `https://api.search.brave.com/res/v1/web/search`
Method: GET; query parameter `q`; authentication header `X-Subscription-Token`.
Use a secret from the environment, never a CLI key argument, inline curl header with expanded key, or committed config.

Parameters used by the helper:
- q: nonempty, at most 600 characters and 75 words.
- count: 1–20.
- offset: 0–9; overlapping pages are possible.
- freshness: pd, pw, pm, py, or YYYY-MM-DDtoYYYY-MM-DD; optional.
- extra_snippets: true.
- text_decorations: false.
- result_filter: web,discussions.

Ordinary web search is used; the helper does not call a separately priced Answers/research/summariser product. Do not assume permission/credits apply to other API products.

Results may include web.results and discussions.results with title, URL, description, extra_snippets and date metadata. Snippets are not full-page access. Page-age metadata is not independently verified publication date.

Response headers can expose X-RateLimit-Limit, Policy, Remaining and Reset. Limits include burst and longer quota windows. On 429 distinguish short throttling from exhausted quota; use bounded delay/backoff. Do not retry credentials/validation errors repeatedly. Read the current plan before large batches.

Safe example (paths relative to this skill):
```sh
python3 scripts/brave_search.py --check-secret
python3 scripts/brave_search.py --query 'site:reddit.com Claude Code cache tool output' \
  --ledger /workspace/research-budget.sqlite --request-ceiling-usd 0.01 --count 10
```
The .01 is an example conservative booked bound, NOT the published price or a verified account rate. Establish a credible bound, including any fees, first. Defaults require an existing ledger so this helper does not spend silently. Both the Brave directory and budget-control directory include the same original `budget_core.py`; the validator checks they match.

Discovery patterns:
- Exact error/setting + version.
- Primary author + mechanism + interview/talk/blog.
- site:x.com / site:twitter.com / site:reddit.com / site:github.com plus counterexamples.
- Follow a social claim to source code and a measurable prediction.
- Record retrieval failure rather than inventing a thread or bypassing login.

Official references:
https://api-dashboard.search.brave.com/api-reference/web/search/get
https://api-dashboard.search.brave.com/documentation/guides/rate-limiting
https://docs.openhands.dev/cookbook/per-conversation-secrets
