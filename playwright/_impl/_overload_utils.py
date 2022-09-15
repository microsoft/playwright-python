import re
from typing import Any


def mark_overload(is_impl: bool = False) -> Any:
    def decorate(func: Any) -> Any:
        f = getattr(func, "__func__", func)
        variant = "impl" if is_impl else "signature"
        setattr(f, "__pw_overload__", variant)
        name = getattr(func, "__name__")
        if variant == "signature" and not re.match(r".*_\d+$", name):
            raise Exception(
                f"Error: {name}. Overload signatures must include a _\\d+ suffix."
            )
        return func

    return decorate


def get_is_overload_impl(f: Any) -> bool:
    return getattr(f, "__pw_overload__", None) == "impl"


def get_is_overload_signature(f: Any) -> bool:
    return getattr(f, "__pw_overload__", None) == "signature"


def get_upstream_name(f: Any) -> str:
    name = getattr(f, "__name__")
    if getattr(f, "__pw_overload__", None) == "signature":
        return re.sub(r"(.*)_(\d+)$", r"\1#\2", name)
    return name


def get_public_name(f: Any) -> str:
    name = getattr(f, "__name__")
    if getattr(f, "__pw_overload__", None) == "signature":
        return re.sub(r"(.*)(_\d+)$", r"\1", name)

    return name
