---
name: fusionlm-source-forensics
description: "Use to verify blog/social claims against original pages, repository code/tests and exact versions, including safe retrieval and licensing."
license: MIT
compatibility: "OpenHands with terminal and file tools; Python 3.10+ for bundled helpers"
metadata:
  version: "1.0.0"
---

# Trace claims to implementation

Use the host browser and terminal first. Optionally use `scripts/fetch_public.py` for a bounded anonymous HTTP fetch. It saves bytes and a small metadata record; it does NOT extract meaning, validate a claim, render JavaScript or bypass access rules.

For every important claim record: URL, author/date, accessed date, source type, quote or code location, commit/version, scope, counterevidence, confidence and decision relevance. Use `references/CLAIM_RECORD.md`.

Prefer original author material. Social posts and small blogs can reveal excellent mechanisms; do not discard them for lacking institutional authority. Equally, distinguish anecdote, benchmark, controlled experiment and speculation. Several copies of the same claim are one source.

Trace promising code through an entry point, data/state path, relevant tests, introducing issue/PR and later regression where feasible. Generated AGENTS.md and README are documented intent, not executed guarantees. A source file existing is not an effectiveness result.

Pin clones and record actual file/line references. Use unauthenticated public access unless an appropriate credential is explicitly supplied. Do not pretend Brave supplies private GitHub access.

Inspect licences per file/component/revision and dependencies before incorporating code. Public source is not automatically MIT; commercial use and redistribution obligations are distinct. Keep proprietary mechanism inferences labelled; no private-access circumvention.

Avoid narrow causal claims from proxies. Event gaps are not API-request gaps; cache-creation totals do not reveal their cause; bytes/4 is an estimate. Missing transcripts mean unknowns, not a clean capability bill of health.

The fetch helper blocks local/private destinations, URL credentials and secret-like query parameters, strips no security barrier, forwards no API credential and disables environment proxies. Redirects are revalidated. Do not use authenticated browser cookies or a third-party mirror with secrets. Browser access may still be needed when anonymous HTTP cannot fetch a source.
