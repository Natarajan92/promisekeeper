# Email and WhatsApp import confirmation fix

Publication authorization, 26 October 2026: the owner subsequently requested pushing the required 007 code, tests, fixtures and product documentation and merging to `main`, while excluding submission documents/folders and personal records. Local/uncommitted statements below describe the original verification checkpoint. Fresh publication checks are recorded in [the publication report](product-007-publication.md); LIVE and human-acceptance limits remain unchanged.

26 October 2026. Local continuation on `007-product-verification-ux`; previous interface cleanup remains uncommitted and is preserved.

The reported preview contained recognised payment wording while the user had selected supporting-context-only review. The API correctly refused to hide a promise as context, but the interface presented that optional checkbox like a required confirmation and offered no correction near the error. It also described message previews as zero CSV rows.

The context-only choice now sits in a clearly labelled optional section. A recognised customer promise selected as context offers **Review payment wording**, which requests a fresh preview with the same original file, reviewed sender, invoice and supplied date. The user must still review the new preview, tick the confirmation and choose **Confirm import**. Nothing is saved by the correction action.

Informational messages without supported payment wording can explicitly request a supporting-context preview. Conditional, ambiguous, malformed and unreviewed-sender wording retains the existing restrictions. The API adds stable codes only to the two correctable review-mode errors; the interface also recognises their exact legacy messages for an already running older API. Message previews describe one message rather than zero CSV rows.

Verification:

- Six new frontend cases cover customer email, remittance email, WhatsApp, legacy API errors, explicit informational context and rejection without a context bypass. The initial five-case candidate had four expected failures and one passing safety check; the corrected focused run passed before the legacy case was added. Final full frontend suite: **240 passed**.
- Four new API cases failed before the change, then passed. Two additional conditional-wording cases preserve the refusal under both review modes. Focused intake, parser, sender, upload robustness and synthetic-pack backend regressions: **446 passed**, with the existing pytest cache-setting warning.
- TypeScript and production build: **passed**.
- Browser upload journeys: **eight passed and one failed** because the existing synthetic-context test attempted to check the now-collapsed optional control. Its helper now opens the optional section; the unchanged financial, limited-result and no-false-closure assertions passed in a focused recheck. All **nine** selected browser checks have passing evidence; the original failed run and traces remain preserved locally.
- New real-browser tests reproduce the supplied Hinglish rupee promise for customer email, remittance email and WhatsApp, prove no document is saved before confirmation, save into the selected workspace/invoice, inspect the exact original content and verify persistence after reload. Desktop error-recovery and 390px confirmation screenshots were visually inspected.

The earlier full backend/Chrome results belong to the preceding interface cleanup; this correction uses the fresh focused results above. No LIVE calls, real customer-data import, customer sending, human acceptance, commit, push or merge was performed.
