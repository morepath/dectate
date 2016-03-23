from confidant.app import App
from confidant.config import Config, Action
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
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    MyApp.configurations.my.l == [('hello', f)]


def test_directive_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
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
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
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

    assert MyApp.configurations.my.message == 'hello'
    assert MyApp.configurations.my.obj is f
    assert SubApp.configurations.my.message == 'hello'
    assert SubApp.configurations.my.obj is f


def test_directive_override():
    config = Config()

    class Registry(object):
        pass

    @App.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
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

    assert MyApp.configurations.my.message == 'hello'
    assert MyApp.configurations.my.obj is f
    assert SubApp.configurations.my.message == 'hello'
    assert SubApp.configurations.my.obj is f2


def test_directive_different_group():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class FooDirective(Action):
        configurations = {
            'foo': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.add(self.message, obj)

    @App.directive('bar')
    class BarDirective(Action):
        configurations = {
            'bar': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, bar):
            return self.message

        def perform(self, obj, bar):
            bar.add(self.message, obj)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    config.commit()

    MyApp.configurations.foo.l == [('hello', f)]
    MyApp.configurations.bar.l == [('hello', g)]


def test_directive_same_group():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class FooDirective(Action):
        configurations = {
            'foo': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.add(self.message, obj)

    @App.directive('bar')
    class BarDirective(Action):
        configurations = {
            'bar': Registry
        }

        def __init__(self, message):
            self.message = message

        # should now conflict
        def group_key(self):
            return FooDirective

        def identifier(self, bar):
            return self.message

        def perform(self, obj, bar):
            bar.add(self.message, obj)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    with pytest.raises(ConflictError):
        config.commit()
