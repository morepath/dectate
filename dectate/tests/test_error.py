from __future__ import annotations

import pytest

from typing import Any, NoReturn

from dectate.app import App, directive
from dectate.config import commit, Action, Composite
from dectate.error import (
    ConflictError,
    ConfigError,
    DirectiveError,
    DirectiveReportError,
)


def test_directive_error_in_action() -> None:
    class FooDirective(Action):
        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> NoReturn:
            raise DirectiveError("A real problem")

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = str(e.value)
    assert value.startswith("A real problem")
    assert value.endswith(' @MyApp.foo("hello")')
    assert "/test_error.py" in value


def test_directive_error_in_composite() -> None:
    class FooDirective(Composite):
        def __init__(self, name: str) -> None:
            self.name = name

        def actions(self, obj: Any) -> NoReturn:
            raise DirectiveError("Something went wrong")

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = str(e.value)
    assert value.startswith("Something went wrong")
    assert value.endswith(' @MyApp.foo("hello")')
    assert "/test_error.py" in value


def test_conflict_error() -> None:
    class FooDirective(Action):
        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> NoReturn:
            raise DirectiveError("A real problem")

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    @MyApp.foo("hello")
    def g() -> None:
        pass

    with pytest.raises(ConflictError) as e:
        commit(MyApp)

    value = str(e.value)
    assert value.startswith("Conflict between:")
    assert ", line " in value
    assert '@MyApp.foo("hello")' in value
    assert "/test_error.py" in value


def test_with_statement_error() -> None:
    class FooDirective(Action):
        def __init__(self, model: type[Any], name: str) -> None:
            self.model = model
            self.name = name

        def identifier(self) -> tuple[type[Any], str]:
            return (self.model, self.name)

        def perform(self, obj: Any) -> NoReturn:
            raise DirectiveError("A real problem")

    class MyApp(App):
        foo = directive(FooDirective)

    class Dummy:
        pass

    with MyApp.foo(model=Dummy) as foo:  # type: ignore[call-arg]

        @foo(name="a")
        def f() -> None:
            pass

        @foo(name="b")
        def g() -> None:
            pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = str(e.value)

    assert value.startswith("A real problem")
    assert value.endswith(' @foo(name="a")')
    assert "/test_error.py" in value


def test_composite_codeinfo_propagation() -> None:
    class SubDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class CompositeDirective(Composite):
        def __init__(self, messages: list[str]) -> None:
            self.messages = messages

        def actions(self, obj: Any) -> list[tuple[SubDirective, Any]]:
            return [(SubDirective(message), obj) for message in self.messages]

    class MyApp(App):
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(["a"])
    def f() -> None:
        pass

    @MyApp.composite(["a"])
    def g() -> None:
        pass

    with pytest.raises(ConflictError) as e:
        commit(MyApp)

    value = str(e.value)

    assert '@MyApp.composite(["a"])' in value
    assert "/test_error.py" in value


def test_type_error_not_enough_arguments() -> None:
    class MyDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    # not enough arguments
    @MyApp.foo()  # type: ignore[call-arg]
    def f() -> None:
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = str(e.value)
    assert "@MyApp.foo()" in value


def test_type_error_too_many_arguments() -> None:
    class MyDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    # too many arguments
    @MyApp.foo("a", "b")  # type: ignore[call-arg]
    def f() -> None:
        pass

    with pytest.raises(DirectiveReportError) as e:
        commit(MyApp)

    value = str(e.value)
    assert 'MyApp.foo("a", "b")' in value


def test_cannot_group_class_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, message: str) -> None:
            pass

    class QuxDirective(Action):
        group_class = BarDirective  # should go to FooDirective instead

        def __init__(self, message: str) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)
        qux = directive(QuxDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_cannot_use_config_with_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        config = {"bar": list}

        group_class = FooDirective

        def __init__(self, message: str) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_cann_inherit_config_with_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

    class BarDirective(FooDirective):
        group_class = FooDirective

        def __init__(self, message: str) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    commit(MyApp)


def test_cannot_use_before_with_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        group_class = FooDirective

        @staticmethod
        def before() -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_can_inherit_before_with_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

        @staticmethod
        def before(foo: list[tuple[str, Any]]) -> None:
            pass

    class BarDirective(FooDirective):
        group_class = FooDirective

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    commit(MyApp)


def test_cannot_use_after_with_group_class() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, foo: list[tuple[str, Any]]) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        group_class = FooDirective

        @staticmethod
        def after() -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_action_without_init() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def identifier(self, foo: list[Any]) -> tuple[()]:
            return ()

        def perform(self, obj: Any, foo: list[Any]) -> None:
            foo.append(obj)

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo()
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.foo == [f]


def test_composite_without_init() -> None:
    class SubDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class CompositeDirective(Composite):
        def actions(self, obj: Any) -> list[tuple[SubDirective, Any]]:
            return [(SubDirective(message), obj) for message in ["a", "b"]]

    class MyApp(App):
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    commit(MyApp)

    @MyApp.composite()
    def f() -> None:
        pass

    commit(MyApp)
