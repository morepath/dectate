from dectate.app import App
from dectate.config import commit, Action, Composite

from dectate.error import (ConflictError, ConfigError, DirectiveError,
                           DirectiveReportError)
from dectate.compat import text_type

import pytest


def test_directive_error_in_action():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            raise DirectiveError("A real problem")

    @MyApp.foo('hello')
    def f():
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = text_type(e.value)
    assert value.startswith("A real problem")
    assert value.endswith(" @MyApp.foo('hello')")
    assert '/test_error.py' in value


def test_directive_error_in_composite():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Composite):
        def __init__(self, name):
            self.name = name

        def actions(self, obj):
            raise DirectiveError("Something went wrong")

    @MyApp.foo('hello')
    def f():
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = text_type(e.value)
    assert value.startswith("Something went wrong")
    assert value.endswith(" @MyApp.foo('hello')")
    assert '/test_error.py' in value


def test_conflict_error():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            raise DirectiveError("A real problem")

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.foo('hello')
    def g():
        pass

    with pytest.raises(ConflictError) as e:
        commit(MyApp)

    value = text_type(e.value)
    assert value.startswith("Conflict between:")
    assert ', line ' in value
    assert "@MyApp.foo('hello')" in value
    assert '/test_error.py' in value


def test_with_statement_error():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self):
            return (self.model, self.name)

        def perform(self, obj):
            raise DirectiveError("A real problem")

    class Dummy(object):
        pass

    with MyApp.foo(model=Dummy) as foo:
        @foo(name='a')
        def f():
            pass

        @foo(name='b')
        def g():
            pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = text_type(e.value)

    assert value.startswith("A real problem")
    assert value.endswith(" @foo(name='a')")
    assert '/test_error.py' in value


def test_composite_codeinfo_propagation():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    @MyApp.composite(['a'])
    def f():
        pass

    @MyApp.composite(['a'])
    def g():
        pass

    with pytest.raises(ConflictError) as e:
        commit(MyApp)

    value = text_type(e.value)

    assert "@MyApp.composite(['a'])" in value
    assert '/test_error.py' in value


def test_type_error_not_enough_arguments():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    # not enough arguments
    @MyApp.foo()
    def f():
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = text_type(e.value)
    assert "@MyApp.foo()" in value


def test_type_error_too_many_arguments():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    # not enough arguments
    @MyApp.foo('a', 'b')
    def f():
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = text_type(e.value)
    assert "@MyApp.foo('a', 'b')" in value


def test_cannot_group_class_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, message):
            pass

    @MyApp.directive('qux')
    class QuxDirective(Action):
        group_class = BarDirective  # should go to FooDirective instead

        def __init__(self, message):
            pass

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_cannot_use_config_with_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        config = {
            'bar': list
        }

        group_class = FooDirective

        def __init__(self, message):
            pass

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_cann_inherit_config_with_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        group_class = FooDirective

        def __init__(self, message):
            pass

    commit(MyApp)


def test_cannot_use_before_with_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        @staticmethod
        def before():
            pass

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_can_inherit_before_with_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

        @staticmethod
        def before(foo):
            pass

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        group_class = FooDirective

    commit(MyApp)


def test_cannot_use_after_with_group_class():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        @staticmethod
        def after():
            pass

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_action_without_init():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def identifier(self, foo):
            return ()

        def perform(self, obj, foo):
            foo.append(obj)

    @MyApp.foo()
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.foo == [f]


def test_composite_without_init():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def actions(self, obj):
            return [(SubDirective(message), obj) for message in ['a', 'b']]

    commit(MyApp)

    @MyApp.composite()
    def f():
        pass

    commit(MyApp)
