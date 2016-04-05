import dectate


class AnApp(dectate.App):
    known = "definitely not a directive"


def other():
    pass


class OtherClass(object):
    pass


@AnApp.directive('foo')
class FooAction(dectate.Action):
    def __init__(self, name):
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj):
        pass
