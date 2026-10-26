"""A bounded bank CSV adapter; no customer allocation or settlement inference."""
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from promisekeeper.application.intake_parsing import parse_csv,source_instant,amount_text,blank_row,header_problem,AMOUNT_HELP,COLUMN_COUNT,MAX_FILE_BYTES,MAX_MINOR
from promisekeeper.domain.money import parse_money

REQUIRED={'date','description','credit'}
ALLOWED=REQUIRED|{'debit','reference','currency','balance'}


BANK_DATE_HELP='Bank dates must be YYYY-MM-DD or DD/MM/YYYY (day first), for example 2026-10-20 or 20/10/2026.'


def bank_day(raw):
    try:
        if '/' in raw:
            # This documented profile is explicitly day-first, never a locale guess.
            raw=datetime.strptime(raw,'%d/%m/%Y').date().isoformat()
        return source_instant(raw)
    except ValueError:
        raise ValueError(f'Unsupported bank date "{raw[:40]}". '+BANK_DATE_HELP) from None


def empty_dash(raw):
    """Indian bank exports print a lone "-" for an empty cell; treat it as empty."""
    return '' if (raw or '').strip()=='-' else (raw or '')


def numeric(raw):
    result=parse_money(amount_text(empty_dash(raw) or '0'),'INR')
    if result.error=='INVALID_PRECISION':raise ValueError('A bank credit/debit has more than two decimal places; paise cannot be rounded.')
    if result.error=='NEGATIVE_AMOUNT':raise ValueError('Bank credits/debits must be nonnegative: a value starting with "-" is not supported (a lone "-" means empty). Put money received in Credit and money paid out in Debit.')
    if result.error or result.minor_units is None:raise ValueError('Bank credit/debit: '+AMOUNT_HELP)
    if not 0<=result.minor_units<=MAX_MINOR:raise ValueError('A bank credit/debit exceeds the supported import limit.')
    return result.minor_units


def bank_identity(row):
    identity=dict(date=row['paid_at'],description=row.get('payer_name',''),minor=str(row['amount_minor']),currency=row['currency'])
    return sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def generated_overlap(left,right):
    return (left['transaction_ref']!=right['transaction_ref'] and
            'GENERATED_FINGERPRINT' in {left.get('reference_origin'),right.get('reference_origin')} and
            bank_identity(left)==bank_identity(right))


def parse_upload(kind,content):
    if kind!='payments':
        rows,errors=parse_csv(kind,content);return rows,errors,[]
    try:
        reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')),strict=True)
        original_headers=reader.fieldnames or []
        headers=[h.strip().casefold() for h in original_headers]
    except (csv.Error,UnicodeError):
        rows,errors=parse_csv(kind,content);return rows,errors,[]
    if 'date' not in headers or 'transaction_ref' in headers:
        rows,errors=parse_csv(kind,content);return rows,errors,[]
    problem=header_problem(headers,REQUIRED,ALLOWED)
    if problem:
        return [],[dict(row=1,message='Bank CSV requires Date, Description, Credit; optional Debit, Reference, Currency, Balance. '+problem)],[]
    if '\x00' in content or len(content.encode('utf-8'))>MAX_FILE_BYTES:
        return [],[dict(row=0,message='Bank file contains NUL bytes or exceeds 256 KiB.')],[]
    rows=[];errors=[]
    warnings=['Bank profile: dates use YYYY-MM-DD or DD/MM/YYYY (day first). Review the interpreted rows. Imported receipts remain UNKNOWN until you check settlement; no customer or invoice is assigned.']
    if 'currency' not in headers:warnings.append('No Currency column: credits are interpreted as INR. Check the statement currency before confirming.')
    lines=content.splitlines(keepends=True);previous=reader.line_num;generated=False;data_rows=0
    try:
        for number,raw in enumerate(reader,2):
            start=previous;previous=reader.line_num
            if blank_row(raw):continue  # spreadsheet ",,,," rows carry no data
            data_rows+=1
            if data_rows>100:
                errors.append(dict(row=number,message='Maximum 100 data rows per upload.'));break
            try:
                if None in raw or any(value is None for value in raw.values()):raise ValueError('Bank row: '+COLUMN_COUNT)
                item={name:raw[original].strip() for name,original in zip(headers,original_headers)}
                if any(len(value)>2000 for value in item.values()):raise ValueError('A bank cell exceeds 2,000 characters.')
                currency=item.get('currency','INR')
                if currency!='INR':raise ValueError('Only INR bank statements are supported; currency must be explicit INR when present.')
                credit=numeric(item['credit']);debit=numeric(item.get('debit',''))
                if credit and debit:raise ValueError('A bank row has both credit and debit; clarify it before importing.')
                if not credit:
                    warnings.append(f'Skipped row {number}: debit-only or no positive receipt. No payment was created.');continue
                paid_at=bank_day(item['date'])
                if datetime.fromisoformat(paid_at)>datetime.now(timezone.utc):raise ValueError('A future bank credit cannot be received yet.')
                if not item['description']:raise ValueError('Bank Description is required for review and identity.')
                reference=empty_dash(item.get('reference',''))
                origin='BANK_REFERENCE' if reference else 'GENERATED_FINGERPRINT'
                if not reference:
                    identity=dict(paid_at=paid_at,payer_name=item['description'],amount_minor=credit,currency=currency)
                    reference='BANK-'+bank_identity(identity)[:32]
                    generated=True
                if len(reference)>120:raise ValueError('Bank Reference exceeds 120 characters.')
                original=''.join(lines[start:previous])
                if len(original)>7000:raise ValueError('A bank source row exceeds the evidence size limit.')
                rows.append(dict(transaction_ref=reference,payer_name=item['description'],payer_alias='',address='',
                    amount=f'{credit//100}.{credit%100:02d}',amount_minor=credit,currency=currency,paid_at=paid_at,
                    invoice_reference='',status='UNKNOWN',reference_origin=origin,_row=number,_original=original))
            except (ValueError,TypeError,OverflowError) as error:
                errors.append(dict(row=number,message=str(error)))
    except (csv.Error,UnicodeError):errors.append(dict(row=0,message='Malformed bank CSV.'))
    if generated:
        warnings.append('Missing bank Reference: BANK- identifiers are generated source fingerprints, not UTRs. Equal date/description/credit/currency rows are treated as identical, including overlapping exports. If identical rows represent distinct real deposits, supply their distinct bank references before importing; do not infer separate receipts.')
    if not rows and not errors:errors.append(dict(row=0,message='No positive bank credits to import.'))
    return rows,errors,warnings
