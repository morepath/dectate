from confidant.app import App, Directive
from confidant.config import Config


def test_directive():
    config = Config()

    l = []

    @App.directive('foo')
    class MyDirective(Directive):
        def __init__(self, app, message):
            super(MyDirective, self).__init__(app)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, registry, obj):
            l.append(self.message)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    assert l == ['hello']
