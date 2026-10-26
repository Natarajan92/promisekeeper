# Separate-file owner workflow

Owner-approved scope, 25 October 2026. The owner approved all six steps and selected
complete implementation/testing over the original 30-minute limit. This feature
uses fictional local uploads, with no connectors, external retrieval or LIVE calls.
It is isolated on `005-csv-reconciliation-demo` from main `f1c9a46`.

## Outcome and acceptance

1. The owner imports a customer master, outstanding invoices and optional existing
   allocations. A read-only preview exposes actual rows and errors. Explicit
   confirmation creates an imported workspace or appends to one; it never copies
   seeded sources. Customer IDs can supply invoice names/aliases/addresses.
2. Receipts are uploaded separately, days or months after issue. Amounts use exact
   INR minor units. Raw receipts start unallocated, including an exact invoice hint.
   Existing allocation exports reuse their links only after settled-record review.
3. Suggestions explain invoice-reference, name/alias and address evidence. Econcity,
   Econ and ECONC remain distinct source values. The owner selects the invoice and
   confirms a positive amount, splits the receipt, or leaves it unallocated. Both
   receipt and invoice caps apply atomically. No score authorizes a payment.
4. Separate remittance/customer `.eml` and WhatsApp `.txt` documents are attached to
   an explicitly selected invoice. Bounded offline text rules inspect actual content,
   retain exact quote spans, currency/date/reference wording and source timezone,
   and show extraction before confirmation. Email requires From, Date and readable
   text/plain. No attachment fetching, PDF, OCR or model inference is introduced.
   Negative/conditional wording, questions, multiple invoice references and more
   than 30 extracted clauses are rejected in preview rather than inferred.
   A message is always a claim or promise, never settlement. Unrecognized wording
   requires explicit context-only review and remains LIMITED under missing-extraction
   safety; recognized payment wording cannot be hidden through that option.
5. After reviewing payment coverage through the visible cutoff, the owner starts
   existing Morning Review. The supplied walkthrough produces EC-101 VERIFY_PAYMENT,
   EC-102 WAIT and AD-201 FOLLOW_UP. Missing coverage must not imply a verified balance.
6. Existing sources, recommendations, exact draft editing/approval/copy and history
   remain available. Nothing is sent. A later ECON-T3 receipt, explicitly allocated
   and reviewed, resolves the original reference claim and supports zero/CLOSE;
   closing the case still requires the owner's separate action.

## Data and failure behavior

SQLite retains immutable original batches, customer/invoice/receipt data,
allocations, documents and ledger-review assertions, scoped to a workspace.
Preview hashes bind content, target and current workspace state. Changed previews,
conflicting IDs, malformed rows, unknown targets and pending/reversed allocations
reject without partial writes. Same-workspace identical imports are no-ops.
Operation receipts replay the original request, including after uncertain responses.
Deletion purges uploaded content and retains only existing safe receipt tombstones.

Every allocation has a unique evidence transaction identity and separately typed
original bank reference. Repeated pieces cannot collapse as duplicate payments.
Claim resolution may combine confirmed pieces of that original reference on the
compatible source day only when their exact sum supports the quoted claim.
This is owner-confirmed fictional settlement, not authenticated bank verification.

New imports/allocations advance the frozen REFERENCE cutoff and conservatively
invalidate completeness, earlier advice and draft approval throughout that imported
workspace. A fresh explicit coverage assertion is necessary. Browser write fences
and returned case revisions prevent old approved text being copied while an import
has an unknown outcome or its new revision is not displayed. Other workspaces and
seeded demonstrations remain isolated. Writes cannot race a running investigation.

## Boundaries and validation

At most six invoices per imported workspace; UTF-8 CSV up to 256 KiB and 100 rows,
fixed headers and positive INR amounts; communications at most 8,000 characters.
No arbitrary column mapping, production authentication, customer data, connectors,
free-form invoice chat or automatic sending is included. The fixture materializer
accepts source-validated uploaded candidates only under uploaded source identities;
original seeded STUB packet qualification remains strict. New LLM roles are not added.

Required evidence: meaningful API/domain tests, frontend recovery tests, full backend
and frontend suites, TypeScript/build, full offline Chrome suite, actual six-step
file-upload journey, desktop/narrow zoom inspection and one fresh independent review.
Human observations and LIVE provider qualification remain unexecuted; automated
rehearsal must be described as such. Publication is a separate owner decision.
