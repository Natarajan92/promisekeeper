-- Widen the catalogue case CHECK to the six registered fixture cases. SQLite cannot ALTER a CHECK,
-- and rebuilding `cases` would disturb its many foreign keys; loosening a CHECK does not change the
-- on-disk format, so the documented writable_schema edit is safe here. Fresh and existing copies match.
PRAGMA writable_schema=ON;
UPDATE sqlite_schema
   SET sql=replace(sql, 'CHECK(catalogue_case_id IN (''PK-001'',''PK-002'',''PK-003''))',
                        'CHECK(catalogue_case_id IN (''PK-001'',''PK-002'',''PK-003'',''PK-004'',''PK-005'',''PK-006''))')
 WHERE type='table' AND name='cases';
PRAGMA writable_schema=RESET;
