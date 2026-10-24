# LIVE evaluation summary

## Final configuration reconciliation

The extraction model, adapter, prompt, candidate policy, temporal policy, evaluator/criteria, manifest and independent findings inventory match the preserved Gate III retry-1 report. Gate IV/V catalogue discovery, recovery tests and measurement tooling do not change those packets or rules. No configuration-change rerun was required. Matching configuration alone did not resolve T060: the earlier batch stopped at 15/153 with 12 correct returns, three provider gaps and 138 unexecuted cases, and remains unchanged.

## Completed fresh Gate V qualification

The separately preserved `live-evaluation-gate-v.json` finished all 153 requested cases at 2026-10-24T15:02:29.525571+00:00. All 152 returned results passed every frozen extraction/provenance/findings/outcome check. One FV-18-B/repeat-1 case remained INCOMPLETE_PROVIDER / PROVIDER_REJECTED_REQUEST. None were unexecuted. The unchanged qualifier returns PASS_WITH_AVAILABILITY_GAPS and qualified=true. That availability gap is retained, not regraded. T060 qualification is satisfied under the frozen criteria.

The requested model was `zai-org/GLM-5.3-Flash`, with adapter 9, prompt 7, evaluator 5, criteria 4 and deadline-by policy 1. The independent findings inventory matched. The provider execution lease was clear at exit and a stop marker prevents automatic continuation. Earlier 15-case, 38-case and other failed/stopped reports remain unchanged. See `live-final-reconciliation.json` for the version comparison and current qualification.

The complete independent invoice/paid/balance/currency/due oracle is STUB fixture evidence. The frozen LIVE evaluator directly checks raw candidate facts and source provenance, findings, action, balance and review time; it does not directly compare every numeric field covered by the fixture oracle. LIVE latency reports measure a separate property and cannot establish extraction correctness. This qualification is not a five-owner usability result or final release acceptance.
