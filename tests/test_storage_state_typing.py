from typing import List, get_type_hints

from playwright._impl._api_structures import (
    OPFSEntry,
    OriginState,
    StorageState,
    VirtualCredential,
)


def test_storage_state_optional_snapshot_fields_are_typed() -> None:
    assert get_type_hints(StorageState)["credentials"] == List[VirtualCredential]
    assert get_type_hints(OriginState)["opfs"] == List[OPFSEntry]
    assert "credentials" in StorageState.__optional_keys__
    assert "opfs" in OriginState.__optional_keys__
    assert {"origin", "localStorage"} <= OriginState.__required_keys__
    assert {"path", "type"} <= OPFSEntry.__required_keys__
    assert "base64" in OPFSEntry.__optional_keys__
