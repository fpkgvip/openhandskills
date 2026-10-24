---
name: fusionlm-budget-control
description: "Use for the shared $290 campaign budget, safe admission/reservations, request accounting, subscriptions versus API estimates and spending reconciliation."
license: MIT
compatibility: "OpenHands with terminal and file tools; Python 3.10+ for bundled helpers"
metadata:
  version: "1.0.0"
---

# One campaign budget, not one budget per agent

Read `references/BUDGET_RULES.md`. Use `scripts/budget_ledger.py` for a local shared SQLite ledger. It prevents over-admission only for operations actually recorded; it is NOT a provider-side billing guarantee.

The owner ceiling is $290 for all additional paid campaign costs together. Do not stack historical budgets or treat remaining wallet balance as permission to spend beyond it. The current operating environment is guaranteed only a Brave credential. Do not infer LLMGateway, Claude or platform-admin access.

1. Initialise once with a limit at or below 290. Refuse conflicting reinitialisation; do not reset a ledger to create headroom.
2. Reconcile controller/runtime and all external costs. Running Qwen itself can cost money outside a helper's visibility. Log conservative bounds or mark metering unknown; do not silently call it free. Unknown external charges block additional paid experiments until bounded, not all offline work.
3. Before an operation reserve its credible maximum incremental charge. Account for outstanding concurrent requests. Use provider-side project/key limits if actually available; do not create keys/accounts or change controls outside authority.
4. Settle from authoritative receipts where known. Conservative booked bounds are explicitly different from actual receipts. Never release an uncertain timed-out request as if unbilled.
5. All agents/processes share one ledger and stable run/request IDs. Settle idempotently; no duplicate allocation.
6. Keep validation capacity. Reallocate internal envelopes autonomously, but never exceed the global ceiling or enable paid continuation to get around a limit.

CLI:
`init --db FILE --limit-usd 290`
`reserve --db FILE --id RUN --usd MAX --category worker`
`settle --db FILE --id RUN --usd ACTUAL --basis actual-receipt`
`release --db FILE --id RUN --reason confirmed-no-charge`
`status --db FILE`

A settlement over its reservation must still be recorded truthfully and reported; reserve larger bounds next time. Local code cannot undo a provider charge. The shipped Brave helper books each attempted request at the declared ceiling as a conservative bound, not a measured invoice.

Do not silently switch subscription usage to API/extra usage. Fixed FusionLM service cost and guaranteed combined Claude cost are different promises. No source or experiment may authorise a budget increase.
