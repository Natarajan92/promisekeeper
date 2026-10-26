"""Fixed, documented CSV formats; no arbitrary paths, executable formulas or imports."""
import csv
from datetime import datetime,time,timezone
import io
import json
import re
from zoneinfo import ZoneInfo
from promisekeeper.domain.money import parse_money
from promisekeeper.domain.dates import deadline

MAX_FILE_BYTES=262144
MAX_MINOR=9_000_000_000_000_000
SCHEMAS={
 'customers':({'customer_id','customer_name'},{'customer_id','customer_name','customer_alias','address'}),
 'invoices':({'invoice_id','amount','currency','issued_at','due_at'},{'invoice_id','customer_id','customer_name','customer_alias','address','amount','currency','issued_at','due_at'}),
 'payments':({'transaction_ref','amount','currency','paid_at'},{'transaction_ref','payer_name','payer_alias','address','amount','currency','paid_at','invoice_reference','status'}),
 'allocations':({'transaction_ref','invoice_id','amount'},{'transaction_ref','invoice_id','amount'}),
}


AMOUNT_HELP='Write the amount as a plain number such as 48000, 48,000.50 or 1,20,000.00 (an optional INR, Rs. or ₹ prefix and /- suffix are accepted).'
# One INR marker before the digits and the common Indian "/-" suffix; nothing else.
INR_CELL=re.compile(r'(?:(?:INR|Rs\.?|₹)\s*)?([0-9][0-9,]*(?:\.[0-9]*)?)(?:\s*/-)?',re.I)


def amount_text(text):
    """The digits of an INR CSV amount cell, without an INR/Rs./₹ marker or /- suffix."""
    match=INR_CELL.fullmatch(text.strip())
    return match[1] if match else text.strip()


def amount_minor(text,currency='INR'):
    if currency!='INR':raise ValueError('Only INR is supported for imports.')
    value=parse_money(amount_text(text),currency)
    if value.error=='INVALID_PRECISION':raise ValueError('Amount has more than two decimal places; paise cannot be rounded. Correct the amount.')
    if value.error=='NEGATIVE_AMOUNT' or value.minor_units==0:raise ValueError('Amount must be positive.')
    if value.error or value.minor_units is None:raise ValueError(AMOUNT_HELP)
    if not 0<value.minor_units<=MAX_MINOR:raise ValueError('Amount exceeds the supported import limit.')
    return value.minor_units


def evidence_amount(text,minor):
    """Evidence keeps the original spelling when the engine reads it directly, else exact decimal text."""
    return text if parse_money(text,'INR').error is None else f'{minor//100}.{minor%100:02d}'


DATE_HELP='Use YYYY-MM-DD (for example 2026-10-20) or an ISO date-time with a timezone.'


def source_instant(text):
    if not text:raise ValueError('A date is required. '+DATE_HELP)
    try:
        if len(text)==10:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):raise ValueError(text)
            value=datetime.combine(datetime.fromisoformat(text).date(),time.min,ZoneInfo('Asia/Kolkata'))
        else:value=datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f'Unsupported date "{text[:40]}". '+DATE_HELP) from None
    if value.tzinfo is None or value.utcoffset() is None:raise ValueError('A timezone or ISO calendar date is required.')
    # Keep the source's timezone. The snapshot already has a separate UTC display
    # instant; claim calendar-day matching needs the original local calendar day.
    return value.isoformat()


COLUMN_COUNT='The column count does not match the header. Put quotes around values that contain commas, for example "48,000" or "12, MG Road".'


def header_problem(headers,required,allowed):
    """A plain message naming missing, repeated or unsupported columns, or None."""
    missing=sorted(required-set(headers));repeated=sorted({h for h in headers if headers.count(h)>1})
    unknown=[h or '(blank)' for h in dict.fromkeys(headers) if h not in allowed]
    if not (missing or repeated or unknown):return None
    parts=[f'{label}: {", ".join(names)}' for label,names in (('missing',missing),('repeated',repeated),('unsupported',unknown)) if names]
    return ('Use the documented column names ('+'; '.join(parts)+'). Required: '+', '.join(sorted(required))+
            ('. Optional: '+', '.join(sorted(allowed-required)) if allowed-required else '')+'. Other columns are not mapped.')


def blank_row(raw):
    values=[v for k,v in raw.items() if k is not None]+list(raw.get(None) or [])
    return all(not (v or '').strip() for v in values)


def parse_csv(kind,content):
    rows=[];errors=[]
    if len(content.encode('utf-8'))>MAX_FILE_BYTES:return [],[dict(row=0,message='File exceeds 256 KiB.')]
    if '\x00' in content:return [],[dict(row=0,message='NUL bytes are not supported.')]
    required,allowed=SCHEMAS[kind]
    try:
        reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')),strict=True)
        # Header names are matched without case or surrounding spaces; order is free.
        headers=[(name or '').strip().casefold() for name in reader.fieldnames or []]
        reader.fieldnames=headers
        problem=header_problem(headers,required,allowed)
        if problem:return [],[dict(row=1,message=problem)]
        lines=content.splitlines(keepends=True);previous=reader.line_num;identities=set();data_rows=0
        for number,raw in enumerate(reader,2):
            start=previous;previous=reader.line_num
            if blank_row(raw):continue  # e.g. spreadsheet ",,,,," rows carry no data
            data_rows+=1  # only data rows count toward the limit
            if data_rows>100:
                errors.append(dict(row=number,message='Maximum 100 data rows per upload.'));break
            try:
                if None in raw or any(v is None for v in raw.values()):raise ValueError(COLUMN_COUNT)
                item={k:v.strip() for k,v in raw.items()}
                if any(len(v)>2000 for v in item.values()):raise ValueError('A cell exceeds 2,000 characters.')
                key=item.get('customer_id' if kind=='customers' else 'invoice_id' if kind=='invoices' else 'transaction_ref','')
                if not key or len(key)>120:raise ValueError('A nonempty identifier of at most 120 characters is required.')
                if kind in {'customers','invoices'} and key in identities:raise ValueError('An identifier is repeated within this file.')
                identities.add(key)
                if kind=='customers':
                    if not item['customer_name']:raise ValueError('Customer name is required.')
                    for field in ['customer_alias','address']:item.setdefault(field,'')
                if kind=='invoices':
                    for field in ['customer_id','customer_name','customer_alias','address']:item.setdefault(field,'')
                    if not item['customer_id'] and not item['customer_name']:raise ValueError('Provide customer_id or customer_name.')
                    item['amount_minor']=amount_minor(item['amount'],item['currency'])
                    item['issued_at']=source_instant(item['issued_at'])
                    due=source_instant(item['due_at'])
                    if datetime.fromisoformat(item['issued_at'])>datetime.now(timezone.utc):raise ValueError('An outstanding invoice cannot be issued in the future.')
                    issued=datetime.fromisoformat(item['issued_at'])
                    calendar_due=len(item['due_at'])==10
                    due_limit=deadline(item['due_at']).expires_at if calendar_due else datetime.fromisoformat(due)
                    if due_limit is None or (issued>=due_limit if calendar_due else issued>due_limit):raise ValueError('Invoice due date cannot precede its issue date.')
                elif kind=='payments':
                    item['amount_minor']=amount_minor(item['amount'],item['currency'])
                    item['paid_at']=source_instant(item['paid_at'])
                    if datetime.fromisoformat(item['paid_at'])>datetime.now(timezone.utc):raise ValueError('A future payment cannot be recorded as received.')
                    for field in ['payer_name','payer_alias','address','invoice_reference']:item.setdefault(field,'')
                    item['status']=item.get('status','UNKNOWN').upper() or 'UNKNOWN'
                    if item['status'] not in {'SETTLED','UNKNOWN','PENDING','REVERSED'}:raise ValueError('Unsupported receipt status.')
                elif kind=='allocations':
                    if not item['invoice_id']:raise ValueError('Invoice reference is required.')
                    item['amount_minor']=amount_minor(item['amount'])
                original=''.join(lines[start:previous])
                if len(original)>7000:raise ValueError('A source row exceeds the evidence size limit.')
                item.update(_row=number,_original=original)
                rows.append(item)
            except (ValueError,TypeError,OverflowError) as error:errors.append(dict(row=number,message=str(error)))
        if not rows and not errors:errors.append(dict(row=2,message='The file contains no data rows.'))
    except (csv.Error,UnicodeError) as error:errors.append(dict(row=0,message='Malformed CSV: '+str(error)))
    return rows,errors


def facts(row):
    return {k:v for k,v in row.items() if not k.startswith('_')}


def stored_facts(row):
    return json.dumps(facts(row),sort_keys=True,ensure_ascii=False,separators=(',',':'))
