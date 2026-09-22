from typing import ClassVar

import dectate


class App(dectate.App):
    pass


@App.directive("foo")
class FooAction(dectate.Action):
    config: ClassVar[dict[str, type]] = {"my": list}

    def __init__(self, name: str) -> None:
        self.name = name

    def identifier(self, my):
        return self.name

    def perform(self, obj, my) -> None:
        my.append((self.name, obj))
