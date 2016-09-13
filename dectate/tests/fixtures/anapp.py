import dectate


class FooAction(dectate.Action):
    def __init__(self, name):
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj):
        pass


class AnApp(dectate.App):
    known = "definitely not a directive"

    foo = dectate.directive(FooAction)


def other():
    pass


class OtherClass(object):
    pass
