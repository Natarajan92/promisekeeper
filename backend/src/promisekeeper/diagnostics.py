"""Allowlisted, redacted diagnostics; raw provider/customer content is excluded."""

import re

_FIELDS = frozenset({"operation_id", "investigation_id", "step", "outcome", "failure_code",
                     "duration_ms", "attempt_number", "requested_model", "returned_model",
                     "schema_version", "adapter_version", "prompt_version", "agent_mode"})


def diagnostic(event: str, fields: dict, *, secrets: tuple[str, ...] = ()) -> dict:
    def clean(value):
        if isinstance(value, str):
            for secret in secrets:
                if secret:
                    value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"(?i)Bearer\s+\S+|sk-[A-Za-z0-9_-]+", "[REDACTED]", value)
            return value[:2048]
        return value if value is None or type(value) in {bool, int, float} else "[OMITTED]"

    name = event if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", event) else "diagnostic_invalid"
    return {"event": name, **{key: clean(value) for key, value in fields.items() if key in _FIELDS}}
