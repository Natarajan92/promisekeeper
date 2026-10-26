"""Interpret reviewed message notation while retaining every raw quoted token."""
import re
from promisekeeper.domain.money import parse_money


def quoted_currency(raw):
    if raw is None:return None
    return 'INR' if raw.casefold() in {'inr','rs','rs.','\u20b9'} else raw


def uploaded_money(candidate):
    currency=quoted_currency(candidate.currency_text) if '-UPLOAD-CUSTOMER-' in candidate.source.source_id else candidate.currency_text
    return parse_money(candidate.amount_text,currency)


def quoted_currency_token(raw,text):
    # Currency may touch the following amount (₹1000, Rs.1000); its left
    # boundary still cannot be a substring of another currency/name.
    return re.search(r'(?<![\w/:+.\-])'+re.escape(raw)+r'(?=\s*[0-9])',text) is not None


def quoted_amount_token(currency,amount,text):
    if currency is None or amount is None or quoted_currency(currency)!='INR':return False
    return re.search(r'(?<![\w/:+.\-])'+re.escape(currency)+r'\s*'+re.escape(amount)+r'(?![0-9,]|\.[0-9])',text) is not None
