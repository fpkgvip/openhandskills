# Budget semantics

The ledger limit cannot exceed $290 and cannot be changed by reinitialisation. Use one shared absolute DB path. SQLite transactions serialize admissions within that DB, not across disconnected copies.

Available = limit − booked/settled charges − outstanding reservations. A provider-side cap and the actual caller's max-output/concurrency controls are still needed. Unwrapped calls, platform inference and cloud fees are not automatically captured.

Exact money is integer micro-USD parsed from decimal strings. Use known credible upper bounds and conservative rounding. `basis=actual-receipt` means an authoritative charge; `basis=upper-bound` means a conservative booked charge; `basis=estimate` is explicitly estimated.

A network timeout may still be billed. Keep or book its reservation until authoritative reconciliation. `release` is only for confirmed zero-cost/before-dispatch operations, never an optimistic refund.

A previous upper-bound/estimate settlement can be reconciled to an actual receipt. An already actual settlement cannot be silently overwritten. An over-reservation/over-cap actual charge must be recorded truthfully; the status shows remaining negative and blocks new reservations.

Brave helper reserves and books each attempted request at its caller-declared ceiling. This intentionally overcounts some errors until reconciled. The counter is not an invoice. It must not be used to imply a measured per-query rate.

For Qwen/OpenHands host costs not visible in this DB, use an explicit conservative reservation or reconcile before admitting more paid work. If genuinely included at no incremental cost, state the basis. If unbounded/unknown, continue offline work and resolve the bound rather than assuming it away.

Keep a reserve for final validation, but reallocate internal phase envelopes autonomously. No need to ask William per experiment within the current authorised scope and verified global headroom.
