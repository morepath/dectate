from dectate import topological_sort, TopologicalSortError

import pytest


def test_topological_sort_on_dcg():
    adjacency = {
        'A': ['B', 'C'],
        'B': ['C', 'D'],
        'C': ['D'],
        'D': ['C'],
        'E': ['F'],
        'F': ['C']}
    with pytest.raises(TopologicalSortError):
        topological_sort(adjacency.keys(), adjacency.__getitem__)


def test_topological_sort_on_dag():
    adjacency = {
        'A': ['B', 'C'],
        'B': ['C', 'D'],
        'C': ['D'],
        'D': [],
        'E': ['F'],
        'F': ['C']}
    nodes = sorted(adjacency.keys())
    # Topological ordering is not unique, and in this implementation
    # the resulting order depends on the initial ordering of the
    # nodes::
    assert topological_sort(nodes, adjacency.__getitem__) == \
        ['D', 'C', 'B', 'A', 'F', 'E']
    assert topological_sort(reversed(nodes), adjacency.__getitem__) == \
        ['D', 'C', 'F', 'E', 'B', 'A']
