import dectate


class App(dectate.App):
    pass


class Other(dectate.App):
    pass


class R(object):
    pass


@App.directive('foo')
class FooAction(dectate.Action):
    def __init__(self, name):
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj):
        pass


@Other.directive('foo')
class OtherFooAction(dectate.Action):
    def __init__(self, name):
        self.name = name

    def identifier(self):
        return self.name

    def perform(self, obj):
        pass
