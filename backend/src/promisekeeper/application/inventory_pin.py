"""Content pins for reviewed evaluation inventories.

The repository stores these files with LF endings (.gitattributes eol=lf), while Windows
working copies may hold CRLF. Pins cover the LF-normalised bytes so a fresh clone and a
CRLF checkout of the same reviewed content verify identically; any content change fails.
"""
import hashlib


def pinned_inventory_bytes(path, expected_hash, label):
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f'{label} inventory bytes differ from reviewed pin')
    return raw
