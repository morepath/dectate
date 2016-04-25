from .error import TopologicalSortError


def topological_sort(l, get_depends):
    """`Topological sort`_

    .. _`Topological sort`: https://en.wikipedia.org/wiki/Topological_sorting

    Given a list of items that depend on each other, sort so that
    dependencies come before the dependent items. Dependency graph must
    be a DAG_.

    .. _DAG: https://en.wikipedia.org/wiki/Directed_acyclic_graph

    :param l: a list of items to sort
    :param get_depends: a function that given an item
      gives other items that this item depends on. This item
      will be sorted after the items it depends on.
    :return: the list sorted topologically.

    """
    result = []
    marked = set()
    temporary_marked = set()

    def visit(n):
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
