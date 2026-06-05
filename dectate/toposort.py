from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar
from .error import TopologicalSortError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_T = TypeVar("_T")


def topological_sort(
    l: Iterable[_T], get_depends: Callable[[_T], Iterable[_T]]  # noqa: E741
) -> list[_T]:
    """`Topological sort`_

    .. _`Topological sort`: https://en.wikipedia.org/wiki/Topological_sorting

    Given an iterable of items that depend on each other, sort so that
    dependencies come before the dependent items. Dependency graph must
    be a DAG_.

    .. _DAG: https://en.wikipedia.org/wiki/Directed_acyclic_graph

    :param l: an iterable of items to sort
    :param get_depends: a function that given an item
      gives other items that this item depends on. This item
      will be sorted after the items it depends on.
    :return: a list of the given items sorted topologically.

    """
    result = []
    marked = set()
    temporary_marked = set()

    def visit(n: _T) -> None:
        if n in marked:
            return
        if n in temporary_marked:
            raise TopologicalSortError("Not a DAG")
        temporary_marked.add(n)
        for m in get_depends(n):
            visit(m)
        marked.add(n)
        result.append(n)

    for n in l:
        visit(n)
    return result
