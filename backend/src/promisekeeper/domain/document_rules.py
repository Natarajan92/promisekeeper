"""Pure, bounded language rules shared by preview and uploaded extraction."""
import re

DATE = r'(?:\d{4}-\d{2}-\d{2}(?:T[^\s,.]+)?|\d{1,2} [A-Za-z]+ \d{4}|next (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|tomorrow|today)'
AMOUNT = re.compile(r'(\bINR(?=\s|[0-9])|\bRs\.?(?=\s|[0-9])|\u20b9)\s*(\S+)',re.I)
QUALIFIED = re.compile(r"\b(?:not|never|no(?![-.])|cannot|can['\u2019]t|won['\u2019]t|don['\u2019]t|didn['\u2019]t|wasn['\u2019]t|haven['\u2019]t|hasn['\u2019]t|unable|unpaid|failed|if|unless|until|subject to|provided|may|might|could|would|hope|perhaps|possibly|pending|expect|after|once|upon|assuming|contingent|dependent|approval|as long as|as soon as|agar|nahi|nahin|jab)\b",re.I)
REPORTED = re.compile(r'\b(?:said|says|told|according to|forwarded|quoted|quotation|wrote|kehte|bola|kaha)\b|["\u201c\u2018][^"\u201d\u2019\n]*(?:will|shall|pay|paid)\b',re.I)
ENGLISH_PROMISE = re.compile(r"\b(?:(?:we|I) (?:will|shall) pay|(?:we|I)['\u2019]ll pay)\b",re.I)
PASSIVE_PROMISE = re.compile(r'^(?:the )?payment(?: of (?:INR|Rs\.?|\u20b9)\s*\S+)? will be (?:made|sent|transferred)\b',re.I)
HINGLISH_PROMISE = re.compile(r'^(?:hum|ham|main)\b.+\b(?:pay|payment)\s+(?:kar\s+(?:denge|dunga|dungi)|karenge|karunga|karungi)\b',re.I)
MONEY = r'(?:INR|Rs\.?|\u20b9)\s*\S+'
PREFIX = r'(?:(?:hi|hello)[,!]\s*)?(?:(?:for|regarding)\s+invoice\s+(?:(?:number|no\.?)\s+)?[A-Za-z0-9][A-Za-z0-9_-]{2,39}\s*[:,]?\s*)?'
DIRECT = r"(?:(?:we|I) (?:will|shall) pay|(?:we|I)['\u2019]ll pay)"
FULL_PROMISE = re.compile(r'(?:'+PREFIX+DIRECT+r'\s+'+MONEY+r'\s+(?:by|on)\s+'+DATE+
    r'|(?:the )?payment of '+MONEY+r' will be (?:made|sent|transferred) by '+DATE+
    r'|(?:hum|ham|main)\s+'+MONEY+r'\s+'+DATE+r'\s+ko (?:pay|payment)\s+(?:kar\s+(?:denge|dunga|dungi)|karenge|karunga|karungi))[.!]?',re.I)
# An invoice id in a label must look like an id: it contains at least one digit,
# so "Invoice unless" / "Invoice: unpaid" are prose, never a harmless label.
INVOICE_ID = r"(?=[A-Za-z_-]*[0-9])[A-Za-z0-9][A-Za-z0-9_-]{2,39}"
SAFE_PROSE = re.compile(r"(?:(?:thanks|thank you(?: for your (?:patience|understanding|support|time|cooperation))?|(?:(?:warm|kind|best) )?regards|sincerely|fictional demonstration only)[.,!]*"
    r"|thank(?:s| you) for (?:checking|following up|the reminder|reaching out|your message)(?: with us)?[.,!]*"
    r"|(?i:namaste|hello|hi|dear)(?:\s+(?:(?-i:[A-Z][A-Za-z.'-]*)|sir|madam|team|ji)){0,3}\s*[,!]?"
    r"|hope you are (?:doing )?well[.!]?"
    r"|invoice\s+"+INVOICE_ID+r"\.?"
    r"|invoice\s*(?::|\#|no\.?)\s*"+INVOICE_ID+r")",re.I)
# The only line exempt from the whole-document qualifier screen: the exact
# "hope" courtesy. Every other SAFE_PROSE line is still screened.
HOPE_COURTESY = re.compile(r"hope you are (?:doing )?well[.!]?",re.I)
GREETING = re.compile(r"(?:namaste|hello|hi|dear)\b",re.I)
INVOICE_LABEL_PREFIX = re.compile(r"invoice\s*(?::|\#|no\.|no\b)?\s*",re.I)
SIGNATURE_DENY = re.compile(r"\b(?:invoice\w*|condition\w*|maybe|later|confirm|only|except|partial\w*|partly|part|half|disput\w*|wrong|issue|problem|sorry|delay|delayed|cancel\w*|hold|soon|next|week|month|permit\w*|depend\w*|allow\w*|tr(?:y|ies|ying)|possib\w*|hopeful\w*|willing|able)\b",re.I)
# Qualifier/payment words (4+ letters) that must not appear anywhere inside a label id.
GLUED_DENY = re.compile(r"unless|unpaid|until|pending|never|cannot|unable|failed|maybe|might|could|would|perhaps|possib|expect|"
                        r"after|assum|conting|depend|approv|later|partial|partly|disput|cancel|delay|paid|payment|refus|wrong|sorry",re.I)
# A short alphabetic sentence is not automatically a signature. Keep the
# supported shape narrow: capitalized names, or a named accounts/finance team.
# Unknown lower-case prose, sentence punctuation and arbitrary role text fail
# closed rather than being silently removed from the promise's context.
SIGNATURE_WORD = r"(?:[A-Z][a-z]+(?:['-][A-Z]?[a-z]+)*|[A-Z]\.)"
SIGNATURE_NAME = re.compile(SIGNATURE_WORD+r"(?:\s+"+SIGNATURE_WORD+r"){0,2}")
SIGNATURE_ROLE = re.compile(r"(?:(?:"+SIGNATURE_WORD+r"\s+){1,2})?"
    r"(?i:accounts|finance)(?:\s+(?i:team|head|department|manager))?")
SIGNATURE_PROSE = re.compile(r"\b(?:tentativ\w*|provisional\w*|estimat\w*|indicativ\w*|effort\w*|endeavou?r\w*|await\w*|funds?|"
    r"uncertain\w*|unconfirmed|approx\w*|potential\w*|intent\w*|target\w*|aim\w*|forecast\w*|probab\w*|likely|presum\w*|propos\w*|"
    r"this|that|it|is|are|was|were|be|been|being|we|you|they|our|your|their|an|the|for|to|from|with|without|and|or|all)\b",re.I)


def is_safe_prose(line):
    """Harmless courtesy/label text. Greeting words get the same screening as signature lines."""
    if SAFE_PROSE.fullmatch(line) is None:return False
    label=INVOICE_LABEL_PREFIX.match(line)
    if GREETING.match(line) or label:
        # For an invoice label only the identifier is screened ("No." is label notation).
        text=line[label.end():] if label else line
        if label:
            # Words glued to digits/underscores/hyphens ("unless1", "2pay", "X1_maybe")
            # have no word boundary, so screen the identifier's letter runs as words
            # and also look for the risky words anywhere inside it.
            words=' '.join(re.split(r'[^A-Za-z]+',text))
            if GLUED_DENY.search(text) or QUALIFIED.search(words) or REPORTED.search(words) or payment_language(words) or SIGNATURE_DENY.search(words):
                return False
        return not (QUALIFIED.search(text) or REPORTED.search(text) or payment_language(text) or SIGNATURE_DENY.search(text))
    return True


def is_signature_block(lines):
    """True for at most three bounded name/role lines, never arbitrary short prose."""
    if not lines or len(lines)>3:return False
    for line in lines:
        if SIGNATURE_NAME.fullmatch(line) is None and SIGNATURE_ROLE.fullmatch(line) is None:return False
        if QUALIFIED.search(line) or REPORTED.search(line) or payment_language(line) or SIGNATURE_DENY.search(line) or SIGNATURE_PROSE.search(line):return False
    return True


def payment_language(text):
    return bool(re.search(r'\b(?:pay|paid|payment|transferred|bhej|karenge)\b',text,re.I))


def promise_language(text):
    return bool(ENGLISH_PROMISE.search(text) or PASSIVE_PROMISE.search(text) or HINGLISH_PROMISE.search(text))
