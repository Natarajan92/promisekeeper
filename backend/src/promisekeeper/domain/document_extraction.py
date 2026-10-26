"""Bounded offline text extraction, with exact quotations and no network/model calls.

This deliberately supports explicit payment/promise wording, not general email understanding.
The owner reviews the result; no message is a verified ledger transaction.
"""
from datetime import datetime, timedelta
from email import policy
from email.parser import Parser
from email.utils import parsedate_to_datetime
import re
from promisekeeper.domain.dates import parse_instant, source_day, deadline, IST
from promisekeeper.domain.money import parse_money
from promisekeeper.domain.quoted_money import quoted_currency
from promisekeeper.domain.document_rules import DATE,AMOUNT,QUALIFIED,REPORTED,payment_language,promise_language,HINGLISH_PROMISE,FULL_PROMISE,HOPE_COURTESY,is_safe_prose,is_signature_block

PLAIN_TRANSFER={'7bit','8bit','binary'}
UTF8_COMPATIBLE={'utf-8','utf8','us-ascii','ascii'}


class DocumentReviewRequired(ValueError):
    """An explicit review-mode correction is needed before this document can be saved."""
    def __init__(self,code,message):
        super().__init__(message)
        self.code=code


def _plain_text(part,content):
    """The text/plain body exactly as written, so every quote stays verbatim in the original."""
    transfer=str(part.get('Content-Transfer-Encoding','7bit')).strip().lower()
    charset=(part.get_content_charset() or 'us-ascii').lower()
    if transfer in PLAIN_TRANSFER:
        # The upload is already Unicode text (read as UTF-8). The str payload is
        # the body as written; get_content() would re-decode non-ASCII text through
        # raw-unicode-escape and turn "₹" into literal backslash text.
        body=part.get_payload()
        if not body.isascii() and charset not in UTF8_COMPATIBLE:
            raise ValueError('Only UTF-8 (or plain ASCII) email text is supported. Save the message as UTF-8 text and upload it again.')
        return body
    body=part.get_content()
    if any(line.strip() and line.strip() not in content for line in body.splitlines()):
        raise ValueError('This email body is base64 or quoted-printable encoded, so its words cannot be quoted exactly from the original. Save the message as plain text and upload it again.')
    return body

def extract_document(content,kind,*,event_at=None,context_only=False,sender_role='CUSTOMER'):
    body=content; speaker=None; source_date=None; warnings=[]; subjects=[]
    if kind in {'remittance_email','customer_email'}:
        message=Parser(policy=policy.default).parsestr(content)
        if not message.get('From') or not message.get('Date'):
            raise ValueError('Email needs From and Date headers; upload a plain-text .eml document.')
        speaker=str(message.get('From'))
        subjects=[str(value).strip() for value in message.get_all('Subject',[])]
        try:source_date=parsedate_to_datetime(str(message.get('Date')))
        except (ValueError,TypeError):raise ValueError('Email Date header is not a supported aware date.') from None
        if message.is_multipart():
            part=message.get_body(preferencelist=('plain',))
            if part is None:raise ValueError('Email needs a text/plain body. HTML/remote attachments are not fetched.')
            body=_plain_text(part,content)
        elif message.get_content_type()=='text/plain':body=_plain_text(message,content)
        else:raise ValueError('Only text/plain email is supported.')
    else:
        # Only the leading Sender/Sent block is metadata. Header-like text
        # after the first body line remains evidence and must be reviewed.
        raw_lines=content.splitlines(); offset=0; metadata={}
        while offset<len(raw_lines):
            raw=raw_lines[offset].strip()
            if not raw:
                offset+=1
                if metadata:break
                continue
            match=re.fullmatch(r'(Sender|Sent):[ \t]*(.+)',raw,re.I)
            if not match:break
            key=match[1].lower()
            if key in metadata:raise ValueError('Repeated source headers are ambiguous; upload one individual message.')
            metadata[key]=match[2].strip(); offset+=1
        body='\n'.join(raw_lines[offset:])
        speaker=metadata.get('sender','Uploaded customer message')
        if 'sent' in metadata:
            parse_instant(metadata['sent'])
            source_date=datetime.fromisoformat(metadata['sent'].replace('Z','+00:00'))
    if source_date is None and event_at:
        parse_instant(event_at)
        source_date=datetime.fromisoformat(event_at.replace('Z','+00:00'))
    if source_date is None or source_date.tzinfo is None or source_date.utcoffset() is None:
        raise ValueError('A source message date with timezone is required; use a Date/Sent header or enter its date.')
    if sender_role not in {'CUSTOMER','OWNER','THIRD_PARTY','UNVERIFIED'}:
        raise ValueError('Choose a supported sender role.')
    if sender_role!='CUSTOMER':
        if not context_only:raise ValueError('Confirm the sender is the customer before extracting a promise. Owner, third-party and unverified messages can be attached as supporting context only.')
        return dict(speaker=speaker,event_at=source_date.isoformat(),sender_role=sender_role,candidates=[],invoice_references=[],
            warnings=['Supporting context only: sender is not a reviewed customer. No customer promise or payment claim was inferred.'],
            extraction_mode='OFFLINE_TEXT_RULES',context_only=True)
    lines=[raw.strip() for raw in body.splitlines() if raw.strip() and not raw.strip().startswith('>')]
    # The bounded parser cannot interpret conditions across sentences/lines. Do
    # not turn a refusal, question or qualified statement into a positive promise.
    # An exact courtesy line (e.g. "Hope you are doing well.") is not a hedge;
    # anything beyond the bounded SAFE_PROSE forms is still screened.
    qualifier_lines=[re.sub(r'\binvoice\s+(?:no\.?|number)\s+','invoice ',line,flags=re.I) for line in lines if not HOPE_COURTESY.fullmatch(line)]
    if any(QUALIFIED.search(line) or REPORTED.search(line) for line in qualifier_lines) and any(payment_language(line) for line in lines):
        raise ValueError('Negative, conditional or ambiguous payment wording is unsupported. Upload an individual unambiguous message; no promise was inferred.')
    candidates=[]
    for line in lines:
        promise=promise_language(line)
        claim_text=re.sub(r'\bwill be (?:made|sent|transferred)\b','',line,flags=re.I)
        claim=bool(re.search(r'\b(?:paid|transferred|payment (?:was |has been )?made|already sent|bhej diya)\b',claim_text,re.I))
        if not claim and not promise:continue
        if claim and promise:raise ValueError('A line mixes a past payment claim with a future promise. Upload individual unambiguous messages.')
        if promise and FULL_PROMISE.fullmatch(line) is None:
            raise ValueError('Promise wording has unsupported context, conditions or attribution. Upload one direct customer statement with its amount/date and no extra conditions.')
        if '?' in line or re.search(r'\bplease\b',line,re.I):
            raise ValueError('Payment questions and requests are unsupported; no positive claim or promise was inferred.')
        if re.search(r'\b(?:or|and|either|between|about|around|approximately|roughly|estimated|less|minus|withholding|deducted|deduction|TDS)\b|\bat (?:least|most)\b|\b(?:up to|instead of|rather than)\b',line,re.I):
            raise ValueError('Coordinated, alternative, approximate or deducted payment wording requires clarification; no amount, date or reference was selected.')
        if content.count(line)>1 and body.count(line)==1 and kind!='whatsapp':
            raise ValueError('The payment wording appears more than once in the original email (for example in both its text and HTML versions), so the exact quote is ambiguous. Upload a plain-text-only copy of the message.')
        if content.count(line)!=1:raise ValueError('Repeated quoted payment wording is ambiguous; upload the individual message.')
        amounts=list(AMOUNT.finditer(line))
        if len(amounts)>1:raise ValueError('Multiple quoted amounts in one line require clarification; no amount was selected.')
        amount=amounts[0] if amounts else None
        amount_text=amount[2].rstrip('.') if amount else None
        amount_error=parse_money(amount_text,'INR').error if amount_text else None
        if amount_error=='INVALID_PRECISION':
            raise ValueError('A quoted INR amount has more than two decimal places; paise cannot be rounded and no amount was selected.')
        if amount_error:
            raise ValueError('A quoted INR amount is not a plain number. Use digits with standard grouping, for example 48000, 48,000.50 or 1,20,000; no amount was guessed.')
        dates=list(re.finditer(r'\b(?:by|on)\s+('+DATE+r')',line,re.I))
        if HINGLISH_PROMISE.search(line):dates+=list(re.finditer(r'('+DATE+r')\s+ko\b',line,re.I))
        if len(dates)>1:raise ValueError('Multiple quoted dates in one line require clarification; no date was selected.')
        date=dates[0] if dates else None
        references=list(re.finditer(r'\b(?:UTR|reference|ref)\s*[:#=\-]?\s*([A-Za-z0-9][A-Za-z0-9_\-/]{1,79})',line,re.I))
        if len(references)>1:raise ValueError('Multiple payment references in one line require clarification; no reference was selected.')
        reference=references[0] if references else None
        interpreted=deadline(date[1],original_at=source_date,allow_weekday=True) if date and promise else None
        interpreted_day=source_day(date[1],original_at=source_date) if date else None
        if date and date[1].lower().startswith('next ') and interpreted and interpreted.expires_at:
            interpreted_day=(interpreted.expires_at.astimezone(IST)-timedelta(days=1)).date()
        item=dict(kind='CLAIM' if claim else 'COMMITMENT',clause=line,amount_text=amount_text,
                  currency_text=amount[1] if amount else None,speaker=speaker,
                  interpreted_currency=quoted_currency(amount[1]) if amount else None,interpreted_date=interpreted_day.isoformat() if interpreted_day else None)
        if claim:item.update(payment_date_text=date[1] if date else None,transaction_reference_text=reference[1] if reference else None)
        else:item.update(date_text=date[1] if date else None)
        candidates.append(item)
        if len(candidates)>30:raise ValueError('Maximum 30 payment claims/promises per document. Upload individual messages.')
    if any(c['kind']=='COMMITMENT' for c in candidates):
        # A subject can qualify the body too. Accept only neutral supported
        # titles; arbitrary subject prose cannot silently become a promise.
        neutral_subject=r'(?:invoice\s+[A-Za-z0-9][A-Za-z0-9_-]{2,39}|(?:promise|payment|remittance)(?:\s+for\s+invoice\s+[A-Za-z0-9][A-Za-z0-9_-]{2,39})?)'
        if len(subjects)>1 or any(subject and re.fullmatch(neutral_subject,subject,re.I) is None for subject in subjects):
            raise ValueError('Email subject has unsupported context or qualifications. Upload an individual unambiguous customer message; the subject was not ignored.')
        clauses={c['clause'] for c in candidates}
        # Courtesy/greeting lines are harmless anywhere; a short name-like
        # signature is accepted only after the last promise line.
        last=max((i for i,line in enumerate(lines) if line in clauses),default=-1)
        loose=[(i,line) for i,line in enumerate(lines) if line not in clauses and not is_safe_prose(line)]
        signature_ok=all(i>last for i,_ in loose) and (not loose or is_signature_block([line for _,line in loose]))
        if not signature_ok or any(raw.lstrip().startswith('>') for raw in body.splitlines()):
            raise ValueError('Surrounding prose or quoted history could qualify this promise. Upload the individual unambiguous customer message; no text was silently ignored.')
    if context_only and candidates:
        raise DocumentReviewRequired('PAYMENT_REVIEW_REQUIRED','This message contains payment wording. Review the claim or promise before adding it to the workspace.')
    if not candidates and not context_only:
        raise DocumentReviewRequired('CONTEXT_REVIEW_REQUIRED','No supported payment claim or promise found. Review the original and explicitly choose supporting context only if appropriate.')
    if not candidates:warnings.append('Supporting context only: no payment claim or promise was extracted.')
    for c in candidates:
        if (c.get('date_text') or '').lower().startswith('next '):
            warnings.append(f"Reviewed weekday rule: {c['date_text']} means {c['interpreted_date']}, the strictly next occurrence after source date {source_date.date().isoformat()}; the same weekday means seven days later. Confirm this interpretation.")
    if candidates:warnings.append('Offline text extraction, reviewed by the owner; messages do not verify settlement.')
    if any(c['currency_text'] not in {None,'INR'} for c in candidates):
        warnings.append('Quoted INR, Rs. and rupee-symbol amounts are interpreted as INR. Original currency wording is retained for review.')
    references=list(dict.fromkeys(re.findall(r'\b(?:invoice\b\s*(?:(?:number\b|no\b\.?|#)\s*)?[:#]?\s*)([A-Za-z0-9][A-Za-z0-9_-]{2,39})',body,re.I)))
    return dict(speaker=speaker,event_at=source_date.isoformat(),sender_role=sender_role,
                candidates=candidates,invoice_references=references,warnings=warnings,
                extraction_mode='OFFLINE_TEXT_RULES',context_only=context_only)
