from typing import Any, Optional, cast


def mark_overload(is_impl: bool = False, overload_name: Optional[str] = None) -> Any:
    def decorate(func: Any) -> Any:
        f = getattr(func, "__func__", func)
        setattr(f, "__pw_overload_impl__", is_impl)
        setattr(f, "__pw_overload_name__", overload_name)
        return func

    return decorate


def get_is_overload_impl(f: Any) -> bool:
    return getattr(f, "__pw_overload_impl__", False)


def get_is_overload(f: Any) -> bool:
    return getattr(f, "__pw_overload_name__", False)


def get_upstream_name(f: Any) -> str:
    return getattr(f, "__pw_overload_name__", cast(str, getattr(f, "__name__")))


def get_public_name(f: Any) -> str:
    name = getattr(f, "__name__")
    if getattr(f, "__pw_overload_name__", None):
        parts = name.split("_")
        return "_".join(parts[:-1])

    return name
