"""Screen untrusted customer text before writing agents see it.

Customer messages are evidence, never instructions. The Promise Extractor still receives the
exact saved text (its output is validated against exact source spans); the writing agents
(Communicator, Tone Reviewer) receive a screened copy with instruction-like sentences removed.
"""
import re

REMOVED = '[instruction-like text removed]'
_SENTENCE = re.compile(r'(?<=[.!?])\s+')
_INSTRUCTION = re.compile('|'.join((
    r'\bignore\b.{0,30}\b(?:rules?|instructions?|previous|above|ledger|evidence|policy)\b',
    r'\b(?:system|developer)\s+(?:note|prompt|message|instructions?)\b',
    r'(?:^|\s)assistant\s*[,:]',
    r'\bto\s+(?:the\s+)?assistant\b',
    r'\byou\s+are\s+now\b',
    r'\bdisregard\b',
    r'\b(?:approve|mark)\b.{0,40}\b(?:draft|invoice|paid|payment|case|message)\b',
    r'\btell\s+the\s+owner\b',
    r'\bwrite\s+that\b',
    r'\binclude\s+(?:our|the|this|my)\b.{0,30}\b(?:account|bank|amount|upi|details)\b',
    r'\bwaive\b',
)), re.I)


def screen_message(text):
    """Return (screened text, whether anything was removed)."""
    sentences = _SENTENCE.split(text.strip())
    kept, flagged = [], False
    for sentence in sentences:
        if _INSTRUCTION.search(sentence):
            flagged = True
            if not kept or kept[-1] != REMOVED:
                kept.append(REMOVED)
        else:
            kept.append(sentence)
    return ' '.join(kept), flagged
