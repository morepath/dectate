from confidant.app import App, Directive
from confidant.config import Config
from confidant.error import ConflictError

import pytest


def test_directive_main():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class MyDirective(Directive):
        configurations = {
            'my': Registry
        }

        def __init__(self, app, frame_info, message):
            super(MyDirective, self).__init__(app, frame_info)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    MyApp.registry.my.l == [('hello', f)]


def test_directive_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class MyDirective(Directive):
        configurations = {
            'my': Registry
        }

        def __init__(self, app, frame_info, message):
            super(MyDirective, self).__init__(app, frame_info)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

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


def test_directive_inherit():
    config = Config()

    class Registry(object):
        pass

    @App.directive('foo')
    class MyDirective(Directive):
        configurations = {
            'my': Registry
        }

        def __init__(self, app, frame_info, message):
            super(MyDirective, self).__init__(app, frame_info)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, obj, my):
            my.message = self.message
            my.obj = obj

    class MyApp(App):
        testing_config = config

    class SubApp(MyApp):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    assert MyApp.registry.my.message == 'hello'
    assert MyApp.registry.my.obj is f
    assert SubApp.registry.my.message == 'hello'
    assert SubApp.registry.my.obj is f


def test_directive_override():
    config = Config()

    class Registry(object):
        pass

    @App.directive('foo')
    class MyDirective(Directive):
        configurations = {
            'my': Registry
        }

        def __init__(self, app, frame_info, message):
            super(MyDirective, self).__init__(app, frame_info)
            self.message = message

        def identifier(self, registry):
            return self.message

        def perform(self, obj, my):
            my.message = self.message
            my.obj = obj

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

    assert MyApp.registry.my.message == 'hello'
    assert MyApp.registry.my.obj is f
    assert SubApp.registry.my.message == 'hello'
    assert SubApp.registry.my.obj is f2
