# Implementation plan: owner experience Phase 2

Spec: [phase2-spec.md](phase2-spec.md). Continue the existing feature checkout;
preserve uncommitted Phase 1. No commit or publication is authorized.

1. Record acceptance/authorization and scope; run installed frontend baseline.
2. Add failing pure comparison tests, then implement sequence-based completed-result
   discovery and saved-field comparison. Test null/large money, source replacements,
   stable commitments, reordered arrays, profile limits, identical/time-only changes.
3. Add failing component tests, then implement a lazy read-only WhatChanged panel,
   bounded pagination, explicit pair selection, original-result/source inspection,
   stale-head/scoping guards and Cedar guidance. Link from Findings and History.
4. Add and run the real STUB Cedar browser journey, asserting no comparison writes,
   immutable results/history and explicit closure. Verify narrow/200% screenshots.
5. Run all installed regression suites and typecheck/build, review the whole increment
   independently, fix material findings with tests, and report actual outcomes.

Shared interfaces: helper supplies sequence-ordered IDs and deterministic differences
to the panel. The panel validates full attempt scope and identity before using its
result. Findings/History supply the current CaseView and existing exact-source callback.
Panel inspection reuses historical Findings without mutation controls. Head changes
do not silently substitute either side. Refresh explicitly resets discovery.

Review focus: oldest-first history and partial latest-pair claims; attempt/result
identity and copy/case checks; source version replacement/removal; null versus zero;
unresolved identities and unsupported profiles; time-only expiry versus causality;
late responses and changing head; read-only source/original inspection and accessible
responsive comparison. Original approval/copy/closure/recovery invariants still apply.
