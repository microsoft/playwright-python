from collections import defaultdict
import inspect
from typing import Callable


def api_overload(fn: Callable) -> Callable:
    """
    Creates an overload that's visible to the api generate scripts. use this decorator instead of `typing.overload` when exposing overloads from `_impl`.
    You will need to suppress mypy errors using a `# type: ignore[no-redef]` comment
    """
    dictionary = inspect.getmodule(fn).__dict__
    overloads_key = "__overloads__"
    if dictionary.get(overloads_key) is None:
        dictionary[overloads_key] = defaultdict(list)
    dictionary[overloads_key][fn.__name__].append(fn)
    return fn
