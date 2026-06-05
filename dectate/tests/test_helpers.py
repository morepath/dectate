from __future__ import annotations

import sys
from ..config import CodeInfo, create_code_info


def current_code_info() -> CodeInfo:
    return create_code_info(sys._getframe(1))


def test_create_code_info() -> None:
    x = current_code_info()
    assert x.path == __file__
    assert x.lineno == 12
    assert x.sourceline == "x = current_code_info()"

    x = eval("current_code_info()")
    assert x.path == "<string>"
    assert x.lineno == 1
    assert x.sourceline is None
