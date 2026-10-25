"""Reviewed inventories are pinned by content, independent of checkout line endings."""
import hashlib
import pytest
from promisekeeper.application.inventory_pin import pinned_inventory_bytes

CONTENT = b'{\n  "a": 1\n}\n'
PIN = hashlib.sha256(CONTENT).hexdigest()


@pytest.mark.parametrize('stored', [CONTENT, CONTENT.replace(b'\n', b'\r\n')])
def test_lf_and_crlf_checkouts_match_the_same_pin(tmp_path, stored):
    path = tmp_path / 'inventory.json'
    path.write_bytes(stored)
    assert pinned_inventory_bytes(path, PIN, 'Test') == CONTENT


def test_changed_content_is_rejected(tmp_path):
    path = tmp_path / 'inventory.json'
    path.write_bytes(CONTENT.replace(b'1', b'2'))
    with pytest.raises(ValueError, match='Test inventory bytes differ from reviewed pin'):
        pinned_inventory_bytes(path, PIN, 'Test')
