import dectate


class FooAction(dectate.Action):
    def __init__(self, name) -> None:
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj) -> None:
        pass


class AnApp(dectate.App):
    known = "definitely not a directive"

    foo = dectate.directive(FooAction)


def other() -> None:
    pass


class OtherClass:
    pass
