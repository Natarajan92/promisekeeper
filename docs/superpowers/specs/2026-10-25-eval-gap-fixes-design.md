# Fix identified system evaluation gaps

The owner authorized fixing the ten failed scenarios and improving their general
behavior. Keep the upload-only fictional workspace, deterministic money and
explicit owner approval/copy/closure. Do not add LIVE calls, connectors, production
authentication or outbound sending. Preserve the original evaluation reports.

Communication needs an explicit sender role (customer, owner, third party or
unverified). The owner selects the role before preview; this is a reviewed
assertion, not authenticated identity. Only customer messages can supply active
payment claims/promises. Other roles may be attached explicitly as supporting
context. Reject conditional/quoted/reported payment statements with actionable
clarification rather than manufacture WAIT. Apply these checks again when uploaded
evidence is investigated, including legacy uploads.

Support bounded direct English, passive future-payment promises and first-person
Hinglish with explicit money/date. Preserve raw quotes/tokens. Recognize INR/Rs./₹
as INR for uploaded monetary candidates, with strict amount/currency provenance;
bank and invoice currency remain strict INR. Interpret `next <weekday>` only for
reviewed uploads as the strictly next occurrence after the source's local calendar
date (same weekday means seven days later); show the resolved date and rule before
confirmation. Historical seeded policy remains unchanged. Other vague dates still
need clarification. No general language-understanding claim.

Accept a documented bank CSV profile Date,Description,Credit with optional
Reference,Debit,Currency,Balance. Display canonical rows and assumptions in preview,
preserve original rows/files, default settlement to UNKNOWN, never auto-allocate.
Generate a clearly labeled source fingerprint only when the bank reference is
missing, deduplicating equal date/description/credit/currency conservatively.
Explain that identical real deposits need distinct bank references; do not silently
count them twice. Skip debit-only rows with explicit preview warnings; reject mixed
credit/debit, malformed/negative amounts, foreign currency and future receipts.
Use ISO dates or explicit DD/MM/YYYY day-first dates; reject other formats.
Reject future-issued outstanding invoices and due dates preceding issue dates.

The new sender review is an intentional API/workflow contract change. Update test
helpers and eval input metadata to simulate the same explicit owner choice, while
preserving expected financial/actions and frozen v1.2 baseline. Record this change
in a new dataset version; do not misrepresent the before/after as identical input
contracts. The final review additionally requires a strict full-message promise
grammar: unsupported prefix/tail/surrounding prose is refused, rather than ignored.
This intentionally restricts mixed-prose capability. M21's earlier WAIT oracle is
retained in old artifacts and explicitly revised to safe refusal in v1.4; the
other64 money/action expectations remain. Add independent adversarial variations
so success is not a fixture lookup.

Exit evidence: 64 unchanged original scenarios plus M21's declared refusal policy pass under the reviewed sender workflow,
expanded safety regressions pass, full backend/frontend/build/browser checks run,
one independent review and any demonstrated findings resolved. LIVE and actual
human observations remain unassessed.
