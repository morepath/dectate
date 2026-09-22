import dectate


class R:
    pass


class FooAction(dectate.Action):
    def __init__(self, name: str) -> None:
        self.name = name

    def identifier(self) -> str:
        return self.name

    def perform(self, obj: R) -> None:
        pass


class App(dectate.App):
    foo = dectate.directive(FooAction)


class Other(dectate.App):
    foo = dectate.directive(FooAction)
