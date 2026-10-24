"""Immutable supported draft facts; review remains an explicit owner decision."""
from dataclasses import dataclass


GREETINGS = ("Hello {recipient},", "Hi {recipient},", "Dear {recipient},")
FOLLOW_UP_REQUESTS = (
    "Could you please share an update on payment?",
    "Please let us know when we can expect payment.",
)
CLARIFICATION_REQUESTS = (
    "Could you please share the missing payment reference or receipt?",
    "Please provide the missing payment reference or receipt so we can review it.",
)
CLOSINGS = ("Thank you.", "Thanks.", "Kind regards.")


@dataclass(frozen=True, slots=True)
class DraftPlan:
    recipient: str
    invoice_id: str
    exact_text: str | None
    no_draft_reason: str | None
    allowed_recipients: tuple[str, ...]
    allowed_clauses: tuple[str, ...]
    source_ids: tuple[str, ...]
