# Fictional manual review packet

Business time: 2026-10-23T10:00:00+05:30. Read the invoice, designated ledger and original customer wording. A message alone does not verify receipt of money.

For each case, state the recorded financial position, the next action, the source supporting it and any question still needing verification. Do not open the answer key until observations are finished.

## PK-001 / Northstar Analytics / NS-104

Ledger availability: AVAILABLE; ledger complete: True.

### PK-001-I1 / INVOICE / version 1

Fictional invoice NS-104; client Northstar Analytics; INR 120,000.00; due 10 October 2026.

Event time: undated; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

### PK-001-L1 / LEDGER / version 1

Fictional verified settled ledger transaction NS-T1; INR 40,000.00; invoice NS-104.

Event time: 2026-10-12T09:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

Recorded ledger fields: `{"amount_text": "40,000.00", "currency_text": "INR", "invoice_id": "NS-104", "settled": true, "transaction_ref": "NS-T1", "verification_status": "VERIFIED"}`

### PK-001-M1 / MESSAGE / version 1

We will pay INR 80,000 by 20 October 2026.

Event time: 2026-10-13T11:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: False.

## PK-002 / Meridian Software / MS-208

Ledger availability: AVAILABLE; ledger complete: True.

### PK-002-I1 / INVOICE / version 1

Fictional invoice MS-208; client Meridian Software; INR 75,000.00; due 18 October 2026.

Event time: undated; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

### PK-002-L1 / LEDGER / version 1

Fictional verified settled ledger transaction MS-T1; INR 25,000.00; invoice MS-208.

Event time: 2026-10-19T09:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

Recorded ledger fields: `{"amount_text": "25,000.00", "currency_text": "INR", "invoice_id": "MS-208", "settled": true, "transaction_ref": "MS-T1", "verification_status": "VERIFIED"}`

### PK-002-M1 / MESSAGE / version 1

We will pay INR 50,000 by 25 October 2026.

Event time: 2026-10-21T15:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: False.

## PK-003 / Cedar Retail Labs / CR-312

Ledger availability: AVAILABLE; ledger complete: True.

### PK-003-I1 / INVOICE / version 1

Fictional invoice CR-312; client Cedar Retail Labs; INR 90,000.00; due 15 October 2026.

Event time: undated; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

### PK-003-L1 / LEDGER / version 1

Fictional verified settled ledger transaction CR-T1; INR 30,000.00; invoice CR-312.

Event time: 2026-10-16T09:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: True.

Recorded ledger fields: `{"amount_text": "30,000.00", "currency_text": "INR", "invoice_id": "CR-312", "settled": true, "transaction_ref": "CR-T1", "verification_status": "VERIFIED"}`

### PK-003-M1 / MESSAGE / version 1

We paid the remaining INR 60,000 today; reference CR-T2.

Event time: 2026-10-22T16:00:00+05:30; arrival: 2026-10-23T10:00:00+05:30.
Availability: AVAILABLE; designated authority: False.
