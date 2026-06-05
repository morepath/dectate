from __future__ import annotations


class Sentinel:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return "<%s>" % self.name


NOT_FOUND = Sentinel("NOT_FOUND")
"""Sentinel value returned if filter value cannot be found on action."""
