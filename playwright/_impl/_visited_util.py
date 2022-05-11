from typing import Any, Dict, List


class StrongDict:
    """Like a Dict, but can use arbitrary values as keys."""

    def __init__(self) -> None:
        self._entries: Dict[int, Any] = {}
        # Python built-in |id| only guarantees uniqueness if objects have overlapping lifetimes,
        # therefore we retain references to ensure overlapping lifetimes and validity of ids.
        self._do_not_gc: List[Any] = []

    def __contains__(self, item: Any) -> bool:
        return id(item) in self._entries

    def __setitem__(self, idx: Any, value: Any) -> None:
        self._do_not_gc.append(idx)
        self._entries[id(idx)] = value

    def __getitem__(self, obj: Any) -> Any:
        return self._entries[id(obj)]

    def lookup_id(self, obj: Any) -> int:
        _id = id(obj)
        assert _id in self._entries
        return _id
