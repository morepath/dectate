import dectate


class App(dectate.App):
    pass


@App.directive('foo')
class FooAction(dectate.Action):
    config = {'my': list}

    def __init__(self, name):
        self.name = name

    def identifier(self, my):
        return self.name

    def perform(self, obj, my):
        my.append((self.name, obj))
