import dectate


class App(dectate.App):
    pass


class Other(dectate.App):
    pass


class R:
    pass


@App.directive("foo")
class FooAction(dectate.Action):
    def __init__(self, name: str) -> None:
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj) -> None:
        pass


@Other.directive("foo")
class OtherFooAction(dectate.Action):
    def __init__(self, name: str) -> None:
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj) -> None:
        pass
