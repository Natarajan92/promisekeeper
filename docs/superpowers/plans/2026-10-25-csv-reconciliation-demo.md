# Implementation plan: separate-file owner workflow

Design: [approved requirements](../specs/2026-10-25-csv-reconciliation-demo-design.md).
Branch: `005-csv-reconciliation-demo`, base main `f1c9a46`. Owner authorized every
phase below and final combined testing; the former 30-minute cutoff is superseded.
Use inline execution and one fresh final reviewer. Do not publish in this increment.

## Phase 1: workspace and independent file intake

Add bounded typed preview/commit APIs, immutable migration tables, exact CSV parsing
and allowlisted sample downloads. Create an empty imported workspace from customers
or invoices; support later appends, master IDs, duplicate/conflict detection and
original-file inspection. Preserve local request guards and operation replay.
Verify preview produces no writes, malformed batches are atomic and scopes are isolated.

## Phase 2: matching and money

Compute explained suggestions from actual payer and invoice metadata. Add explicit
partial/split allocations and imported existing links, retaining original bank refs
separately from unique allocation IDs. Enforce exact receipt/invoice caps, statuses,
revision checks and investigation exclusion. Add explicit ledger coverage at the
current cutoff. Reuse existing deterministic reconciliation, lifecycle and history.
Verify delayed claims, same-receipt repeated pieces, split invoices, original history,
duplicate replay, stale previews, pending receipts and coverage invalidation.

## Phase 3: separate communication documents

Parse text/plain emails and WhatsApp text offline. Preserve originals, exact quotes,
source dates, amounts/references and promise wording; show warnings/errors before
confirmation. Feed uploaded sources through source validation in the STUB adapter,
without weakening seeded candidate checks. Context-only unsupported messages remain
limited. Supply independent customer, invoice, initial/later receipts, allocation,
remittance, promise and paid-claim files with a reproducible walkthrough.
Verify filename independence, quote grounding, precision/currency boundaries,
original-file scope, persisted restart and non-authoritative messages.

## Phase 4: owner experience

Build upload/preview/confirm, extraction/source inspection, suggested matches,
explicit allocation/splitting and coverage controls. Integrate imported saved copies
with existing Morning Review, recommendation/evidence, exact draft approval/copy and
history. Add scoped uncertain-operation recovery and revision fences. Use existing
casebook typography/palette, clear status language, keyboard labels, wrapping text
and contained table scrolling. Check actual desktop and 390px/200% presentation.

## Phase 5: combined verification and review

After implementation, run full backend and frontend suites and TypeScript/build,
then full serial offline Chrome including the actual six-step sample upload journey.
Record genuine failures and any justified isolated reruns; preserve product deadlines.
Inspect screenshots, request one fresh whole-diff reviewer, fix material findings and
repeat affected checks. Report actual counts and remaining format/demo limits in
`reports/csv-reconciliation-demo.md`. Keep all work reviewable and uncommitted.

## Constitution compliance

Written requirements preceded implementation, and the owner's expanded file/message
scope was recorded before the affected work. Deterministic code owns money and
persistence; source quotes are validated; every message approval and closure remains
human-operated. Only fictional local data is used. No new LLM role, real-data
connector, LIVE evaluation or production-safety claim is introduced. Existing release
fixtures remain intact; this bounded imported-workspace mode extends their input
path. The owner explicitly authorized continuous phases, overriding the default
phase-boundary stop. No constitutional principle is weakened or amended.
