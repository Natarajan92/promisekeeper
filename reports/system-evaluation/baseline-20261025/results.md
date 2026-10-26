# Offline system evaluation

Dataset: promisekeeper-system-v1 (64 cases). Mode: STUB; LIVE unqualified; human study unexecuted.

| Case | Track | Verdict | Failed checks | Duration ms |
|---|---|---|---|---:|
| M01 | contract | PASS |  | 5390.0 |
| M02 | contract | PASS |  | 907.0 |
| M03 | contract | PASS |  | 1000.0 |
| M04 | contract | PASS |  | 1250.0 |
| M05 | contract | PASS |  | 860.0 |
| M06 | contract | PASS |  | 1047.0 |
| M07 | contract | PASS |  | 891.0 |
| M08 | contract | PASS |  | 968.0 |
| M09 | contract | PASS |  | 1000.0 |
| M10 | contract | PASS |  | 1188.0 |
| M11 | contract | PASS |  | 984.0 |
| M12 | contract | PASS |  | 1000.0 |
| M13 | contract | PASS |  | 937.0 |
| M14 | contract | PASS |  | 969.0 |
| M15 | contract | PASS |  | 890.0 |
| M16 | contract | PASS |  | 922.0 |
| M17 | contract | PASS |  | 922.0 |
| M18 | contract | PASS |  | 1031.0 |
| M19 | contract | PASS |  | 954.0 |
| M20 | contract | PASS |  | 891.0 |
| M21 | contract | PASS |  | 1000.0 |
| M22 | contract | PASS |  | 734.0 |
| M23 | capability | FAIL | action | 813.0 |
| M24 | capability | FAIL | accepted, action | 1219.0 |
| M25 | capability | FAIL | action | 1281.0 |
| M26 | capability | FAIL | accepted, action | 1313.0 |
| M27 | capability | FAIL | accepted, action | 1265.0 |
| M28 | safety | FAIL | action, safe_action | 1219.0 |
| M29 | safety | PASS |  | 1281.0 |
| M30 | safety | FAIL | action, safe_action | 1125.0 |
| M31 | safety | PASS |  | 1344.0 |
| M32 | safety | FAIL | action, safe_action | 1281.0 |
| M33 | safety | PASS |  | 1500.0 |
| M34 | contract | PASS |  | 1282.0 |
| M35 | contract | PASS |  | 1422.0 |
| M36 | contract | PASS |  | 1641.0 |
| I01 | contract | PASS |  | 797.0 |
| I02 | contract | PASS |  | 735.0 |
| I03 | contract | PASS |  | 750.0 |
| I04 | contract | PASS |  | 765.0 |
| I05 | contract | PASS |  | 938.0 |
| I06 | contract | PASS |  | 2266.0 |
| I07 | contract | PASS |  | 828.0 |
| I08 | contract | PASS |  | 3328.0 |
| I09 | contract | PASS |  | 844.0 |
| I10 | contract | PASS |  | 860.0 |
| I11 | capability | FAIL | accepted | 875.0 |
| I12 | contract | FAIL | accepted | 907.0 |
| A01 | contract | PASS |  | 1609.0 |
| A02 | contract | PASS |  | 1812.0 |
| A03 | contract | PASS |  | 1906.0 |
| A04 | contract | PASS |  | 1921.0 |
| A05 | contract | PASS |  | 3984.0 |
| A06 | contract | FAIL | accepted, balance_minor, remaining_minor | 3016.0 |
| A07 | contract | PASS |  | 3610.0 |
| A08 | contract | PASS |  | 1891.0 |
| W01 | contract | PASS |  | 1016.0 |
| W02 | contract | PASS |  | 1453.0 |
| W03 | contract | PASS |  | 1500.0 |
| W04 | contract | PASS |  | 2344.0 |
| W05 | contract | PASS |  | 2563.0 |
| W06 | contract | PASS |  | 3563.0 |
| W07 | contract | ERROR | executed | 3000.0 |
| W08 | contract | PASS |  | 1672.0 |

{"PASS": 52, "FAIL": 11, "ERROR": 1, "UNEXECUTED": 0}

Individual literal expectations, inputs and actual observations are in results.json.
