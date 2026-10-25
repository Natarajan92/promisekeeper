"""The Communicator's single personal-note paragraph: warmth only, never facts or instructions.

The note sits directly after the greeting. Every amount, date, invoice and request stays in
template-owned clauses; a note that carries any of them, or reads like an instruction, is blocked.
"""
import re

NOTE_MAX_CHARS = 400
PLACEHOLDER = re.compile(r'\[[^\]]*\]|\{[^}]*\}|<[^>]*>|\b(?:TODO|TBD)\b', re.I)
FEE_OR_THREAT = re.compile(r'\b(?:fee|fees|interest|penalty|legal|threat|lawsuit)\b', re.I)
PAYMENT_INSTRUCTION = re.compile(r'\b(?:account|bank|UPI|IBAN|routing|transfer to|pay into)\b', re.I)
PAYMENT_ASSERTION = re.compile(r'\b(?:not paid|non-payment|never paid|payment (?:is |was )?(?:verified|received|settled))\b', re.I)
FOREIGN_CURRENCY = re.compile(r'\b(?:USD|EUR|GBP|AUD|CAD|JPY)\b|[$€£]')
STATED_AMOUNT = re.compile(r'\b(?:INR|USD|EUR|GBP)\s*[0-9,]+(?:\.[0-9]+)?')
INSTRUCTION_LIKE = re.compile(r'\b(?:ignore|instructions?|prompt|system|approve|disregard)\b', re.I)
# The note is warmth only: any payment, money, time or contact topic belongs to code-owned clauses.
PAYMENT_TOPIC = re.compile(r'\b(?:pay\w*|paid|settle\w*|balance\w*|amount\w*|invoice\w*|dues?|overdue|owe[ds]?|owing|outstanding|'
                           r'waive\w*|forgiv\w*|discount\w*|refund\w*|cancel\w*|clos(?:e|ed|ing|ure)|clear(?:ed|ing)?|remit\w*|transfer\w*|'
                           r'lawyers?|attorneys?|courts?|collections?|'
                           r'rupees?|rs|inr|lakhs?|crores?|hundreds?|thousands?|millions?|'
                           r'(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\w*|'
                           r'deadlines?|today|tomorrow|tonight|yesterday|weeks?|weekend|months?|'
                           r'monday|tuesday|wednesday|thursday|friday|saturday|sunday|'
                           r'january|february|march|april|june|july|august|september|october|november|december|'
                           r'e-?mail\w*|phone\w*|call\w*|whatsapp|paypal|links?|url|https?|www|escalat\w*|receipt\w*|reference\w*)\b', re.I)


def note_reasons(note: str) -> tuple[str, ...]:
    checks = (
        (len(note) > NOTE_MAX_CHARS, 'NOTE_TOO_LONG'),
        ('\n' in note, 'NOTE_MULTI_PARAGRAPH'),
        (re.search(r'\d', note), 'NOTE_HAS_DIGITS'),
        (FOREIGN_CURRENCY.search(note) or re.search(r'\bINR\b|₹', note), 'UNSUPPORTED_CURRENCY'),
        (FEE_OR_THREAT.search(note), 'UNSUPPORTED_FEE_OR_THREAT'),
        (PAYMENT_INSTRUCTION.search(note), 'UNSUPPORTED_PAYMENT_INSTRUCTION'),
        (PAYMENT_ASSERTION.search(note), 'UNSUPPORTED_PAYMENT_ASSERTION'),
        (PLACEHOLDER.search(note), 'UNRESOLVED_PLACEHOLDER'),
        (INSTRUCTION_LIKE.search(note), 'NOTE_INSTRUCTION_LIKE'),
        (PAYMENT_TOPIC.search(note), 'NOTE_PAYMENT_TOPIC'),
    )
    return tuple(reason for failed, reason in checks if failed)


def compose_with_note(plan_text: str, note: str | None) -> str:
    if note is None or not note.strip():
        return plan_text
    greeting, separator, rest = plan_text.partition('\n\n')
    return greeting + '\n\n' + note.strip() + (separator + rest if separator else '')
