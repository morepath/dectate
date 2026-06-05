from __future__ import annotations

from ..sentinel import NOT_FOUND


def test_not_found() -> None:
    assert repr(NOT_FOUND) == "<NOT_FOUND>"
