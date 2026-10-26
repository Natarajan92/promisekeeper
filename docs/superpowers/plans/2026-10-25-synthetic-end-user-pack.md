# Synthetic end-user pack implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one fresh final review.

**Goal:** Give the owner ready-to-upload fictional files and independently expected
outcomes, then exercise the real application with those files.

**Architecture:** One six-invoice workspace exercises valid end-user activity;
separate challenge files exercise rejections and limited evidence without polluting
the main walkthrough. A deterministic standard-library generator refreshes dates
relative to an explicit demo day and creates a downloadable ZIP.

**Tech stack:** Python CSV/email/ZIP files, existing STUB API/SQLite, Playwright.

## Requirements and constraints

- Stay on the existing feature branch; preserve all prior uncommitted work.
- Four fictional customers, six invoices, 30/45/60/90-day payment delays, payer
  name/address differences, duplicate exports, partial/full/split receipts, paise,
  unallocated excess, pending/reversed/unknown receipts and delayed settlement.
- Separate source emails/WhatsApp: supported remittance, missing-payment claim,
  active/expired promises, repeated pieces sharing an original bank reference.
- Independently authored expected balances/actions, not values copied from SUT.
- Challenge malformed CSV/amounts/currency/dates, allocation caps/status/ownership,
  document ambiguity, context-only/relative-date/currency limitations and injection.
- Plain UTF-8 CSV, EML, TXT only for upload. README and expected-results metadata
  are instructions/oracles. No LIVE calls, real data, messages, publication or auth.

## Tasks

1. Write a failing deterministic-pack/API test. Implement
   `fixtures/synthetic_pack.py: generate_pack(output, as_of)` and its CLI. Generate
   ready-to-use files under `docs/demo-import/synthetic-pack` and a ZIP alongside it.
2. Test main and challenge files through real preview/commit/allocation/investigation
   APIs. Check exact money, no automatic assignment, replay/history and no writes on
   invalid inputs. Reproduce and repair demonstrated application bugs conservatively.
3. Run an actual browser upload journey with the generated files: preview, existing
   allocations, manual repeated/split pieces, documents, coverage, Morning Review,
   approval and delayed receipt. Include actionable invalid preview checks.
4. Write observed results and limits, link the pack from the walkthrough, run
   appropriate regressions and one fresh independent review. Fix material findings,
   record truthful remaining gaps, and leave changes local/uncommitted.

## Review focus

Date expiry and timezone boundaries; tautological expected outcomes; multiple amounts
or dates in a clause; duplicate bank references with split pieces; unsafe content
changing financial facts; parser rejection versus safe LIMITED behavior.

## Rulings

The user directly requested data and testing within the already implemented formats;
no further design selection is needed. Existing005 feature branch is the requested
isolation. No extra worktree or commits; Windows-native runtime ledger replaces the
POSIX helper. Test only fictional STUB behavior; human/LIVE acceptance is not inferred.
