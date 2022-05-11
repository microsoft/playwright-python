from typing import Dict, Generic, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class Map(Generic[K, V]):
    def __init__(self) -> None:
        self._entries: Dict[int, Tuple[K, V]] = {}

    def __contains__(self, item: K) -> bool:
        return id(item) in self._entries

    def __setitem__(self, idx: K, value: V) -> None:
        self._entries[id(idx)] = (idx, value)

    def __getitem__(self, obj: K) -> V:
        return self._entries[id(obj)][1]
