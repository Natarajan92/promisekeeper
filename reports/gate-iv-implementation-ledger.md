# Gate IV execution ledger

Plan: `specs/001-payment-case-mvp/tasks.md`, T062-T084. Spec: `specs/001-payment-case-mvp/spec.md`; API, UI and data-model contracts are binding.

Owner authorization: 24 October 2026, after Gate III approval and push as `078c4db`. T060 remains an outstanding LIVE qualification requirement. Gate V is unauthorized. Gate IV implementation remains local pending its review.

## Preflight and interfaces

- Requirements checklist 16/16; safety checklist 38/38. Extension hooks absent. SpecKit prerequisite discovery succeeded using a process-scoped execution-policy override; no persistent machine-policy change.
- Baseline: 612 backend tests passed, one opt-in LIVE skip; 26 components and 37 real browser journeys passed; typecheck/build passed.
- T062/T066 -> T065/T067/T068: frozen DraftPlan and build_draft_plan/validate_draft interfaces carry supported exact clauses and no-draft reasons. Wire DTOs remain in contracts/reviews.py.
- T063/T065-T069 -> T064/T070/T071: CaseView includes immutable draft, review history, generation attempt, no-draft reason and server eligibility; mutation receipts bind exact payload and originating copy/case.
- T072 -> T073-T084: lifecycle work starts after draft integration journeys pass; existing scenario preview/confirmation and deletion services are reused.
- Ruling: Continue in the established feature checkout, consistent with preceding approved gates and existing execution ledger. No new worktree or main-branch implementation.
- Ruling: The current owner authorization permits starting Gate IV with T060 outstanding; no LIVE or release qualification is inferred and no criteria/report is regraded.
- Ruling: Existing SpecKit task format and this ledger replace shell brief helpers designed for numbered Superpowers task headings. Preserve meaningful RED/GREEN evidence and task completion here.

## Progress

- Draft domain/template and backend transaction groups dispatched with separate file ownership; frontend review starts with component tests. No customer transmission capability is added.

- T062/T066 domain/template slice: 46 new draft checks; 209 domain checks passed after behavioral RED. Frozen plan, verified-balance templates, neutral clarification, no-draft reasons and finite clause grammar implemented.
- T064/T070/T071 UI slice: seven behavioral failures preceded implementation; committed-save recovery regression failed then passed. Task review found newer typing erased by an in-flight save and no changed-head recovery choice. Both reproduced with two failing regressions, fixed and passed 10/10 component checks; scoped independent re-review approved.
- Draft-browser integration first run: three passed; test expectation incorrectly required a customer draft after PK-001-U1 although the deterministic result becomes WAIT (corrected test); lost-save recovery exposed a strict receipt lookup envelope gap, and failed-draft browser control exposed missing retry eligibility. Both API gaps reproduced and fixed by backend implementer. One additional browser context failed to start during a local worker memory failure; tests now reuse their isolated page fixture. No pass inferred from infrastructure failure.

- Backend task review initially found no blockers and independently ran 13 checks. Implementer then identified a process-death gap between committed result and draft reservation; parent retained it as Important and requested an atomic durable intent plus restart regression before accepting T067/T072. This is still open until the covering check and scoped review pass.

- T063/T065/T067-T069: 15 targeted real-SQLite/API checks passed, including strict receipt recovery, epoch/head fencing, independent generator failure/retry, automatic-retry preservation, deletion replay and process death after result commit. Initial task review passed 13 checks; the subsequent atomic-intent fix passed two independently executed scoped regressions and review. Required draft intent commits with its saved recommendation; planning errors record durable FAILED intent.
- T072: all nine real Chrome/API/SQLite draft journeys passed. UI 10/10 review checks, domain 209 checks (46 new), and backend 15 focused checks passed; no sending route or state exists. US3 checkpoint permits beginning T073-T084; final integrated full-suite verification remains T084.

- T073/T075-T080 backend slice: 22 new US4 checks plus 34 existing relevant regressions passed (56 total). RED exposed history ownership/event reads spanning concurrent deletion; BEGIN now preserves the original read snapshot. Exact zero CLOSE ignores only the same nonmaterial INVOICE_DATE_UNRESOLVED issue as existing domain policy; regression proved prior blanket rejection then passed. Historical draft reads, strict lifecycle/disposition receipt lookup and content-free deletion behavior are implemented.
- T074/T081/T082 frontend slice: 13 history component checks pass with 49 total UI checks. RED covered missing controls, exact-ID deletion, late preview loading recovery and omitted prior findings; full FindingsView now renders original historical findings/source links. Checked confirmations are tied to exact copy/case/revision/result identity. Pending-deletion receipts clear selected copy only after confirmed outcome, including recovery.
- Ruling: Keep the frozen production fixture catalogue/live manifest unchanged. One fixed test-only conflicting invoice event exercises later CLOSED-case evidence through the real preview/confirmation service; production startup never registers it. Cost if wrong: the later-conflict demonstration remains test-harness-only rather than a selectable product event.

- Final independent whole-change review ran five targeted real-SQLite checks successfully. One Important finding remains open: separate Review/History hooks can retain stale pending state after an initiating panel unmounts; a confirmed deletion can also miss stable-scope selection/discovery handling after navigation. Consolidated final fix wave requested with tab/sibling/deletion regressions.
- Final: minor (deferred): fictional-update selector uses the catalogue-wide event union, so a baseline PK-001 default can offer a variant-only clock event that the server rejects at preview. Server confirmation authority remains strict; improve variant-scoped option discovery in a subsequent reviewed change.

- Final integrated pre-fix baseline: 695 backend checks passed, one deliberate LIVE skip and existing dependency warning; UI49/typecheck/build passed; all51 real browser journeys passed. Narrow390px draft/200%-root-font screenshot inspected with no horizontal clipping.
- Final review recovery regression: three new real-browser checks ran against the pre-fix bundle; save across Review to History and deletion across History to Findings failed as reported; deletion across selection of another copy already passed. Consolidated fix wave and scoped re-review remain pending; T084 stays open.

- Final fix wave: six real-App regressions failed before implementation, then passed with existing review/history coverage. Shared pending/authoritative-receipt coordination now survives initiating-panel unmount; stable App handles committed deletion only for its originating copy. Exact matching buffer cleanup preserves newer text and other-copy pending work.
- Final scoped re-review: Important finding ADDRESSED; six independently run App regressions passed and no new Critical/Important findings. The Minor variant-selector issue remains deferred.
- T084 complete: backend695/one LIVE skip; frontend55 serial/typecheck/build; all54 real browser journeys passed. Three covering browser regressions passed after two meaningful pre-fix failures. Gate V T085-T100 remains unchecked/unauthorized. Stop for owner review; Gate IV changes remain local/uncommitted.
- Final: Ruling: T060/provider reliability remain unjudged by Gate IV offline checks; no live calls were made. Cost if wrong: release still requires a healthy qualified provider run.
- Final: Ruling: Gate V whole-flow faults, performance and human acceptance remain unexecuted and unauthorized. Cost if wrong: these checks cannot support a release claim.
- Final: Ruling: General prose validation and arbitrary recipients remain outside the approved finite grammar/catalogue. Cost if wrong: otherwise reasonable free wording may need supported alternatives or new reviewed scope.

## Owner-authorized selector follow-up

- The 24 October 2026 owner instruction authorizes finishing, approving and publishing Gate IV, followed by Gate V. Earlier stop/authorization statements above record their historical checkpoints.
- Addressed the deferred Minor selector finding: catalogue event metadata now lists `eligible_variant_ids` (null denotes baseline), derived from the existing registered event tables. The History selector uses the selected saved copy's variant, case and clock mode; unavailable copy metadata offers no event. Preview and confirmation retain their existing server checks. Frozen catalogue financial content and LIVE evaluation material are unchanged.
- RED: the new API regression failed because eligibility metadata was absent; the real-App baseline regression failed because it offered `FV-17-EVIDENCE-RUN-START`. GREEN: 11 scenario API/integration checks and 23 case/history UI checks passed; typecheck passed. The App checks cover both baseline exclusion and FV-17-EVIDENCE inclusion. The existing Starlette/httpx dependency deprecation warning remains. Full publication verification is recorded by the root session separately.

- Owner publication follow-up: independent selector review validated all eight events against baseline and 40 variants; no blockers. Fresh full backend696/one intentional LIVE skip, serial UI57 and production build passed. Earlier deferred-Minor and unauthorized-V lines above are historical; the owner authorized Gate IV publication and Gate V on 24 October 2026.

- Publication: all54 real browser journeys passed after the selector correction; owner approval received and normal fast-forward push authorized. No open Critical/Important/Minor review findings in Gate IV.
