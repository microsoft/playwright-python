from dataclasses import dataclass
from typing import Dict, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class Entry(Generic[K, V]):
    public_id: int
    key: K
    value: V


class Map(Generic[K, V]):
    def __init__(self) -> None:
        self._entries: Dict[int, Entry] = {}
        self._last_id = 0

    def __contains__(self, item: K) -> bool:
        return id(item) in self._entries

    def __setitem__(self, idx: K, value: V) -> None:
        self._last_id += 1
        self._entries[id(idx)] = Entry(public_id=self._last_id, key=idx, value=value)

    def __getitem__(self, obj: K) -> Entry:
        return self._entries[id(obj)].value

    def lookup_id(self, obj: K) -> int:
        return self._entries[id(obj)].public_id
