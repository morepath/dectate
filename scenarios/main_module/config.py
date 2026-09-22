from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import dectate

if TYPE_CHECKING:
    from collections.abc import Callable


class FooAction(dectate.Action):
    config: ClassVar[dict[str, Callable[..., Any]]] = {"my": list}

    def __init__(self, name: str) -> None:
        self.name = name

    def identifier(self, my: list[tuple[str, object]]) -> str:
        return self.name

    def perform(self, obj: object, my: list[tuple[str, object]]) -> None:
        my.append((self.name, obj))


class App(dectate.App):
    foo = dectate.directive(FooAction)
