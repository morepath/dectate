from confidant.app import App, Directive
from confidant.config import Config
from confidant.error import ConflictError

import pytest


def test_directive_main():
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


def test_directive_conflict():
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

    @MyApp.foo('hello')
    def f2():
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_directive_override():
    config = Config()

    @App.directive('foo')
    class MyDirective(Directive):
        def __init__(self, app, message):
            super(MyDirective, self).__init__(app)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, registry, obj):
            registry.message = self.message
            registry.obj = obj

    class MyApp(App):
        testing_config = config

    class SubApp(MyApp):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    @SubApp.foo('hello')
    def f2():
        pass

    config.commit()

    assert MyApp.registry.message == 'hello'
    assert MyApp.registry.obj is f
    assert SubApp.registry.message == 'hello'
    assert SubApp.registry.obj is f2
