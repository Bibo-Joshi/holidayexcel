from collections.abc import Collection
from typing import TypeVar

_T = TypeVar("_T")


def scn_to_set(argument: _T | Collection[_T] | None) -> set[_T]:
    """Converts a single object or a collection of objects to a collection of objects.
    If the argument is None, an empty collection is returned.
    """
    if argument is None:
        return set()
    if isinstance(argument, str):
        return {argument}  # type: ignore[arg-type]
    if isinstance(argument, Collection):
        return set(argument)
    return {argument}
