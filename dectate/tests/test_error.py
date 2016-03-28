from dectate.app import App
from dectate.config import commit, Action, Composite

from dectate.error import ConflictError, DirectiveError, DirectiveReportError
from dectate.compat import text_type

import pytest


def test_directive_error():
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
        commit([MyApp])

    value = text_type(e.value)
    assert value.startswith("A real problem")
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
        commit([MyApp])

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
        commit([MyApp])

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
        commit([MyApp])

    value = text_type(e.value)

    assert "@MyApp.composite(['a'])" in value
    assert '/test_error.py' in value
