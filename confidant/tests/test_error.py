from confidant.app import App
from confidant.config import Config, Action

from confidant.error import ConflictError, DirectiveError, DirectiveReportError
from confidant.compat import text_type

import pytest


def test_directive_error():
    config = Config()

    class MyApp(App):
        testing_config = config

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
        config.commit()

    value = text_type(e.value)
    assert value.startswith("A real problem")
    assert value.endswith(" @MyApp.foo('hello')")
    assert '/test_error.py' in value


def test_conflict_error():
    config = Config()

    class MyApp(App):
        testing_config = config

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
        config.commit()

    value = text_type(e.value)
    assert value.startswith("Conflict between:")
    assert ', line ' in value
    assert "@MyApp.foo('hello')" in value
    assert '/test_error.py' in value


def test_with_statement_error():
    config = Config()

    class MyApp(App):
        testing_config = config

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
        config.commit()

    value = text_type(e.value)

    assert value.startswith("A real problem")
    assert value.endswith(" @foo(name='a')")
    assert '/test_error.py' in value
