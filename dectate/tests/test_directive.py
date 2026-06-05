from __future__ import annotations

import pytest

from typing import TYPE_CHECKING, Any

from dectate.app import App, directive
from dectate.config import commit, Action, Composite
from dectate.error import ConflictError, ConfigError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def test_simple() -> None:
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

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("hello", f)]


def test_decorator() -> None:
    # NOTE: This style is not supported by mypy, since class decorators
    #       currently cannot change the type of the attribute.
    class MyApp(App):
        @directive
        class foo(Action):
            config = {"my": list}

            def __init__(self, message: str) -> None:
                self.message = message

            def identifier(self, my: list[tuple[str, Any]]) -> str:
                return self.message

            def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
                my.append((self.message, obj))

    @MyApp.foo("hello")  # type: ignore[operator]
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("hello", f)]


def test_commit_method() -> None:
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

    @MyApp.foo("hello")
    def f() -> None:
        pass

    result = MyApp.commit()

    assert MyApp.config.my == [("hello", f)]
    assert list(result) == [MyApp]


def test_directive_name() -> None:
    class MyDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[MyDirective]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[MyDirective]) -> None:
            my.append(self)

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    MyApp.commit()

    MyApp.config.my[
        0
    ].directive.directive_name == "foo"  # pyright: ignore[reportUnusedExpression]


def test_conflict_same_directive() -> None:
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

    @MyApp.foo("hello")
    def f() -> None:
        pass

    @MyApp.foo("hello")
    def f2() -> None:
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_app_inherit() -> None:
    class Registry:
        message: str
        obj: Any

    class MyDirective(Action):
        config = {"my": Registry}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: Registry) -> str:
            return self.message

        def perform(self, obj: Any, my: Registry) -> None:
            my.message = self.message
            my.obj = obj

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp, SubApp)

    assert MyApp.config.my.message == "hello"
    assert MyApp.config.my.obj is f
    assert SubApp.config.my.message == "hello"
    assert SubApp.config.my.obj is f


def test_app_override() -> None:
    class Registry:
        message: str
        obj: Any

    class MyDirective(Action):
        config = {"my": Registry}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: Registry) -> str:
            return self.message

        def perform(self, obj: Any, my: Registry) -> None:
            my.message = self.message
            my.obj = obj

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

    @MyApp.foo("hello")
    def f() -> None:
        pass

    @SubApp.foo("hello")
    def f2() -> None:
        pass

    commit(MyApp, SubApp)

    assert MyApp.config.my.message == "hello"
    assert MyApp.config.my.obj is f
    assert SubApp.config.my.message == "hello"
    assert SubApp.config.my.obj is f2


def test_different_group_no_conflict() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(
            self, obj: Callable[..., Any], foo: list[tuple[str, Any]]
        ) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        config = {"bar": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, bar: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(
            self, obj: Callable[..., Any], bar: list[tuple[str, Any]]
        ) -> None:
            bar.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    @MyApp.bar("hello")
    def g() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.foo == [("hello", f)]
    assert MyApp.config.bar == [("hello", g)]


def test_same_group_conflict() -> None:
    class FooDirective(Action):
        config = {"foo": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(
            self, obj: Callable[..., Any], foo: list[tuple[str, Any]]
        ) -> None:
            foo.append((self.message, obj))

    class BarDirective(Action):
        # should now conflict
        group_class = FooDirective

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, foo: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(
            self, obj: Callable[..., Any], foo: list[tuple[str, Any]]
        ) -> None:
            foo.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    @MyApp.bar("hello")
    def g() -> None:
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_conflict() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str, others: list[str]) -> None:
            self.message = message
            self.others = others

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def discriminators(self, my: list[tuple[str, Any]]) -> list[str]:
            return self.others

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo("f", ["a"])
    def f() -> None:
        pass

    @MyApp.foo("g", ["a", "b"])
    def g() -> None:
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_same_group_conflict() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str, others: list[str]) -> None:
            self.message = message
            self.others = others

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def discriminators(self, my: list[tuple[str, Any]]) -> list[str]:
            return self.others

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class BarDirective(FooDirective):
        group_class = FooDirective

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo("f", ["a"])
    def f() -> None:
        pass

    @MyApp.bar("g", ["a", "b"])
    def g() -> None:
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_no_conflict() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str, others: list[str]) -> None:
            self.message = message
            self.others = others

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def discriminators(self, my: list[tuple[str, Any]]) -> list[str]:
            return self.others

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo("f", ["a"])
    def f() -> None:
        pass

    @MyApp.foo("g", ["b"])
    def g() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("f", f), ("g", g)]


def test_discriminator_different_group_no_conflict() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str, others: list[str]) -> None:
            self.message = message
            self.others = others

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def discriminators(self, my: list[tuple[str, Any]]) -> list[str]:
            return self.others

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class BarDirective(FooDirective):
        # will have its own group key so in a different group
        depends = [FooDirective]

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo("f", ["a"])
    def f() -> None:
        pass

    @MyApp.bar("g", ["a", "b"])
    def g() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("f", f), ("g", g)]


def test_depends() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class BarDirective(Action):
        depends = [FooDirective]

        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.bar("a")
    def g() -> None:
        pass

    @MyApp.foo("b")
    def f() -> None:
        pass

    commit(MyApp)

    # since bar depends on foo, it should be executed last
    assert MyApp.config.my == [("b", f), ("a", g)]


def test_composite() -> None:
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

    @MyApp.composite(["a", "b", "c"])
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("a", f), ("b", f), ("c", f)]


def test_composite_change_object() -> None:
    class SubDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    def other() -> None:
        pass

    class CompositeDirective(Composite):
        def __init__(self, messages: list[str]) -> None:
            self.messages = messages

        def actions(self, obj: Any) -> list[tuple[SubDirective, Any]]:
            return [(SubDirective(message), other) for message in self.messages]

    class MyApp(App):
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(["a", "b", "c"])
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("a", other), ("b", other), ("c", other)]


def test_composite_private_sub() -> None:
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
        # mark sub as private by using the underscore
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(["a", "b", "c"])
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("a", f), ("b", f), ("c", f)]


def test_composite_private_composite() -> None:
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
        sub = directive(SubDirective)
        _composite = directive(CompositeDirective)

    @MyApp.sub("a")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [("a", f)]


def test_nested_composite() -> None:
    class SubDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class SubCompositeDirective(Composite):
        def __init__(self, message: str) -> None:
            self.message = message

        def actions(self, obj: Any) -> Generator[tuple[SubDirective, Any]]:
            yield SubDirective(self.message + "_0"), obj
            yield SubDirective(self.message + "_1"), obj

    class CompositeDirective(Composite):
        def __init__(self, messages: list[str]) -> None:
            self.messages = messages

        def actions(self, obj: Any) -> list[tuple[SubCompositeDirective, Any]]:
            return [
                (SubCompositeDirective(message), obj)
                for message in self.messages
            ]

    class MyApp(App):
        sub = directive(SubDirective)
        subcomposite = directive(SubCompositeDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(["a", "b", "c"])
    def f() -> None:
        pass

    commit(MyApp)

    # since bar depends on foo, it should be executed last
    assert MyApp.config.my == [
        ("a_0", f),
        ("a_1", f),
        ("b_0", f),
        ("b_1", f),
        ("c_0", f),
        ("c_1", f),
    ]


def test_with_statement_kw() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, model: type[Any], name: str) -> None:
            self.model = model
            self.name = name

        def identifier(
            self, my: list[tuple[type[Any], str, Any]]
        ) -> tuple[type[Any], str]:
            return (self.model, self.name)

        def perform(
            self, obj: Any, my: list[tuple[type[Any], str, Any]]
        ) -> None:
            my.append((self.model, self.name, obj))

    class Dummy:
        pass

    class MyApp(App):
        foo = directive(FooDirective)

    # NOTE: This is another use-case that's not well supported by
    #       type checkers. This would require some kind of partial
    #       type transform, so we're allowed to omit required arguments
    #       For now this will require either providing a default for
    #       those parameters or ignoring the type error. This seems
    #       still better than completely erasing the signature of the
    #       directive. We instead provide a new helper attribute partial.
    with MyApp.foo(model=Dummy) as foo:  # type: ignore

        @foo(name="a")
        def f() -> None:
            pass

        @foo(name="b")
        def g() -> None:
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, "a", f),
        (Dummy, "b", g),
    ]


def test_with_statement_args() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, model: type[Any], name: str) -> None:
            self.model = model
            self.name = name

        def identifier(
            self, my: list[tuple[type[Any], str, Any]]
        ) -> tuple[type[Any], str]:
            return (self.model, self.name)

        def perform(
            self, obj: Any, my: list[tuple[type[Any], str, Any]]
        ) -> None:
            my.append((self.model, self.name, obj))

    class MyApp(App):
        foo = directive(FooDirective)

    class Dummy:
        pass

    with MyApp.foo(Dummy) as foo:  # type: ignore[call-arg]

        @foo("a")
        def f() -> None:
            pass

        @foo("b")
        def g() -> None:
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, "a", f),
        (Dummy, "b", g),
    ]


def test_partial_with_statement_kw() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, model: type[Any], name: str) -> None:
            self.model = model
            self.name = name

        def identifier(
            self, my: list[tuple[type[Any], str, Any]]
        ) -> tuple[type[Any], str]:
            return (self.model, self.name)

        def perform(
            self, obj: Any, my: list[tuple[type[Any], str, Any]]
        ) -> None:
            my.append((self.model, self.name, obj))

    class Dummy:
        pass

    class MyApp(App):
        foo = directive(FooDirective)

    with MyApp.foo.partial(model=Dummy) as foo:

        @foo(name="a")
        def f() -> None:
            pass

        @foo(name="b")
        def g() -> None:
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, "a", f),
        (Dummy, "b", g),
    ]


def test_partial_with_statement_args() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, model: type[Any], name: str) -> None:
            self.model = model
            self.name = name

        def identifier(
            self, my: list[tuple[type[Any], str, Any]]
        ) -> tuple[type[Any], str]:
            return (self.model, self.name)

        def perform(
            self, obj: Any, my: list[tuple[type[Any], str, Any]]
        ) -> None:
            my.append((self.model, self.name, obj))

    class MyApp(App):
        foo = directive(FooDirective)

    class Dummy:
        pass

    with MyApp.foo.partial(Dummy) as foo:

        @foo("a")
        def f() -> None:
            pass

        @foo("b")
        def g() -> None:
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, "a", f),
        (Dummy, "b", g),
    ]


def test_before() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.before = False

        def add(self, name: str, obj: Any) -> None:
            assert self.before
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def before(my: Registry) -> None:
            my.before = True

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo(name="hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.li == [
        ("hello", f),
    ]


def test_before_without_use() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.before = False

        def add(self, name: str, obj: Any) -> None:
            assert self.before
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def before(my: Registry) -> None:
            my.before = True

    class MyApp(App):
        foo = directive(FooDirective)

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.li == []


def test_before_group() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.before = False

        def add(self, name: str, obj: Any) -> None:
            assert self.before
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def before(my: Registry) -> None:
            my.before = True

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.bar(name="bye")
    def f() -> None:
        pass

    @MyApp.foo(name="hello")
    def g() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.li == [
        ("hello", g),
    ]


def test_config_group() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.name

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.name, obj))

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.name

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.bar(name="bye")
    def f() -> None:
        pass

    @MyApp.foo(name="hello")
    def g() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my == [
        ("bye", f),
        ("hello", g),
    ]


def test_before_group_without_use() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.before = False

        def add(self, name: str, obj: Any) -> None:
            assert self.before
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def before(my: Registry) -> None:
            my.before = True

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.li == []


def test_after() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.after = False

        def add(self, name: str, obj: Any) -> None:
            assert not self.after
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def after(my: Registry) -> None:
            my.after = True

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo(name="hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.my.after
    assert MyApp.config.my.li == [
        ("hello", f),
    ]


def test_after_without_use() -> None:
    class Registry:
        def __init__(self) -> None:
            self.li: list[tuple[str, Any]] = []
            self.after = False

        def add(self, name: str, obj: Any) -> None:
            assert not self.after
            self.li.append((name, obj))

    class FooDirective(Action):
        config = {"my": Registry}

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, my: Registry) -> str:
            return self.name

        def perform(self, obj: Any, my: Registry) -> None:
            my.add(self.name, obj)

        @staticmethod
        def after(my: Registry) -> None:
            my.after = True

    class MyApp(App):
        foo = directive(FooDirective)

    commit(MyApp)

    assert MyApp.config.my.after
    assert MyApp.config.my.li == []


def test_action_loop_should_conflict() -> None:
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

    for i in range(2):

        @MyApp.foo("hello")
        def f() -> None:
            pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_action_init_only_during_commit() -> None:
    init_called = []

    class MyDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            init_called.append("there")
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    assert init_called == []

    commit(MyApp)

    assert init_called == ["there"]


def test_registry_should_exist_even_without_directive_use() -> None:
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

    commit(MyApp)

    assert MyApp.config.my == []


def test_registry_should_exist_even_without_directive_use_subclass() -> None:
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

    class SubApp(MyApp):
        pass

    commit(MyApp, SubApp)

    assert MyApp.config.my == []
    assert SubApp.config.my == []


def test_rerun_commit() -> None:
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

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    # and again
    commit(MyApp)

    assert MyApp.config.my == [("hello", f)]


def test_rerun_commit_add_directive() -> None:
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

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    @MyApp.foo("bye")
    def g() -> None:
        pass

    # and again
    commit(MyApp)

    assert MyApp.config.my == [("hello", f), ("bye", g)]


def test_order_subclass() -> None:
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

    class SubApp(MyApp):
        pass

    @SubApp.foo("c")
    def h() -> None:
        pass

    @MyApp.foo("a")
    def f() -> None:
        pass

    @MyApp.foo("b")
    def g() -> None:
        pass

    commit(MyApp, SubApp)

    assert SubApp.config.my == [("a", f), ("b", g), ("c", h)]


def test_registry_single_factory_argument() -> None:
    class Other:
        factory_arguments = {"my": list}

        def __init__(self, my: list[tuple[str, Any]]) -> None:
            self.my = my

    class MyDirective(Action):
        config = {"my": list, "other": Other}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]], other: Other) -> str:
            return self.message

        def perform(
            self, obj: Any, my: list[tuple[str, Any]], other: Other
        ) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [("hello", f)]


def test_registry_factory_argument_introduces_new_registry() -> None:
    class Other:
        factory_arguments = {"my": list}

        def __init__(self, my: list[tuple[str, Any]]) -> None:
            self.my = my

    class MyDirective(Action):
        config = {"other": Other}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, other: Other) -> str:
            return self.message

        def perform(self, obj: Any, other: Other) -> None:
            other.my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [("hello", f)]
    assert MyApp.config.my is MyApp.config.other.my


def test_registry_factory_argument_introduces_new_registry_subclass() -> None:
    class IsUsedElsewhere:
        poked = False

    class Other:
        factory_arguments = {"my": IsUsedElsewhere}

        def __init__(self, my: IsUsedElsewhere) -> None:
            self.my = my

    class MyDirective(Action):
        config = {"other": Other}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, other: Other) -> str:
            return self.message

        def perform(self, obj: Any, other: Other) -> None:
            assert not other.my.poked
            other.my.poked = True

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.other.my.poked
    assert MyApp.config.my is MyApp.config.other.my

    commit(SubApp)


def test_registry_multiple_factory_arguments() -> None:
    class Other:
        factory_arguments = {"my": list, "my2": list}

        def __init__(self, my: list[tuple[str, Any]], my2: list[str]) -> None:
            self.my = my
            self.my2 = my2

    class MyDirective(Action):
        config = {"my": list, "my2": list, "other": Other}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(
            self, my: list[tuple[str, Any]], my2: list[str], other: Other
        ) -> str:
            return self.message

        def perform(
            self,
            obj: Any,
            my: list[tuple[str, Any]],
            my2: list[str],
            other: Other,
        ) -> None:
            my.append((self.message, obj))
            my2.append("blah")

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [("hello", f)]
    assert MyApp.config.other.my2 == ["blah"]


def test_registry_factory_arguments_depends() -> None:
    class Other:
        factory_arguments = {"my": list}

        def __init__(self, my: list[tuple[str, Any]]) -> None:
            self.my = my

    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class BarDirective(Action):
        config = {"other": Other}

        depends = [FooDirective]

        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self, other: Other) -> str:
            return self.name

        def perform(self, obj: Any, other: Other) -> None:
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo("hello")
    def f() -> None:
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [("hello", f)]


def test_registry_factory_arguments_depends_complex() -> None:
    class Registry:
        pass

    class PredicateRegistry:
        factory_arguments = {"registry": Registry}

        def __init__(self, registry: Registry) -> None:
            self.registry = registry

    class SettingAction(Action):
        config = {"registry": Registry}

        # NOTE: mypy will complain about SettingAction being abstract
        #       without these overrides, which is correct, but not
        #       relevant for this test.
        if TYPE_CHECKING:

            def identifier(self, **kw: Any) -> Any:
                pass

            def perform(self, obj: Any, **kw: Any) -> None:
                pass

    class PredicateAction(Action):
        config = {"predicate_registry": PredicateRegistry}

        depends = [SettingAction]

        if TYPE_CHECKING:

            def identifier(self, **kw: Any) -> Any:
                pass

            def perform(self, obj: Any, **kw: Any) -> None:
                pass

    class ViewAction(Action):
        config = {"registry": Registry}

        depends = [PredicateAction]

    class MyApp(App):
        setting = directive(SettingAction)
        predicate = directive(PredicateAction)
        view = directive(ViewAction)

    commit(MyApp)

    assert MyApp.config.registry is MyApp.config.predicate_registry.registry


def test_is_committed() -> None:
    class MyApp(App):
        pass

    assert not MyApp.is_committed()

    commit(MyApp)

    assert MyApp.is_committed()


def test_registry_config_inconsistent() -> None:
    class FooDirective(Action):
        config = {"my": list}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]]) -> str:
            return self.message

        def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
            my.append((self.message, obj))

    class BarDirective(Action):
        config = {"my": dict}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: dict[str, Any]) -> str:
            return self.message

        def perform(self, obj: Any, my: dict[str, Any]) -> None:
            my[self.message] = obj

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_inconsistent() -> None:
    class Other:
        factory_arguments = {"my": list}

        def __init__(self, my: list[Any]) -> None:
            self.my = my

    class YetAnother:
        factory_arguments = {"my": dict}

        def __init__(self, my: dict[str, Any]) -> None:
            self.my = my

    class MyDirective(Action):
        config = {"other": Other, "yetanother": YetAnother}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, other: Other, yetanother: YetAnother) -> str:
            return self.message

        def perform(
            self, obj: Any, other: Other, yetanother: YetAnother
        ) -> None:
            pass

    class MyApp(App):
        foo = directive(MyDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_and_config_inconsistent() -> None:
    class Other:
        factory_arguments = {"my": dict}

        def __init__(self, my: dict[str, Any]) -> None:
            self.my = my

    class MyDirective(Action):
        config = {"my": list, "other": Other}

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(self, my: list[tuple[str, Any]], other: Other) -> str:
            return self.message

        def perform(
            self, obj: Any, my: list[tuple[str, Any]], other: Other
        ) -> None:
            my.append((self.message, obj))

    class MyApp(App):
        foo = directive(MyDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


# making this global to ensure the repr is the same
# on Python 3.5 and earlier versions (see PEP 3155)
class ReprDirective(Action):
    """Doc"""

    config = {"my": list}

    def __init__(self, message: str) -> None:
        self.message = message

    def identifier(self, my: list[tuple[str, Any]]) -> str:
        return self.message

    def perform(self, obj: Any, my: list[tuple[str, Any]]) -> None:
        my.append((self.message, obj))


class MyAppForRepr(App):
    foo = directive(ReprDirective)


def test_directive_repr() -> None:
    MyAppForRepr.commit()

    assert repr(MyAppForRepr.foo) == (
        "<bound method AppMeta.foo of "
        "<class 'dectate.tests.test_directive.MyAppForRepr'>>"
    )


def test_app_class_passed_into_action() -> None:
    class MyDirective(Action):
        config = {"my": list}

        app_class_arg = True

        def __init__(self, message: str) -> None:
            self.message = message

        def identifier(
            self, app_class: type[MyApp], my: list[tuple[str, Any]]
        ) -> str:
            return self.message

        def perform(
            self, obj: Any, app_class: type[MyApp], my: list[tuple[str, Any]]
        ) -> None:
            app_class.touched.append(None)
            my.append((self.message, obj))

    class MyApp(App):
        touched: list[None] = []

        foo = directive(MyDirective)

    class SubApp(MyApp):
        touched: list[None] = []

    @MyApp.foo("hello")
    def f() -> None:
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched == [None]

    # the subclass is not affected until we commit for it too
    assert not SubApp.touched

    commit(SubApp)

    assert SubApp.touched == [None]


def test_app_class_passed_into_factory() -> None:
    # NOTE: mypy grabs the wrong version of MyApp if we don't define
    #       it before it's used
    class BaseApp(App):
        touched: bool

    class Other:
        factory_arguments = {"my": list}

        app_class_arg = True

        def __init__(self, my: list[Any], app_class: type[BaseApp]) -> None:
            self.my = my
            self.app_class = app_class

        def touch(self) -> None:
            self.app_class.touched = True

    class MyDirective(Action):
        config = {"other": Other}

        def __init__(self) -> None:
            pass

        def identifier(self, other: Other) -> tuple[()]:
            return ()

        def perform(self, obj: Any, other: Other) -> None:
            other.touch()

    class MyApp(BaseApp):
        touched = False

        foo = directive(MyDirective)

    @MyApp.foo()
    def f() -> None:
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched


def test_app_class_passed_into_factory_no_factory_arguments() -> None:
    # NOTE: mypy grabs the wrong version of MyApp if we don't define
    #       it before it's used
    class BaseApp(App):
        touched: bool

    class Other:
        app_class_arg = True

        def __init__(self, app_class: type[BaseApp]) -> None:
            self.app_class = app_class

        def touch(self) -> None:
            self.app_class.touched = True

    class MyDirective(Action):
        config = {"other": Other}

        def __init__(self) -> None:
            pass

        def identifier(self, other: Other) -> tuple[()]:
            return ()

        def perform(self, obj: Any, other: Other) -> None:
            other.touch()

    class MyApp(BaseApp):
        touched = False

        foo = directive(MyDirective)

    @MyApp.foo()
    def f() -> None:
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched


def test_app_class_passed_into_factory_separation() -> None:
    # NOTE: mypy grabs the wrong version of MyApp if we don't define
    #       it before it's used
    class BaseApp(App):
        touched: bool

    class Other:
        factory_arguments = {"my": list}

        app_class_arg = True

        def __init__(self, my: list[Any], app_class: type[BaseApp]) -> None:
            self.my = my
            self.app_class = app_class

        def touch(self) -> None:
            self.app_class.touched = True

    class MyDirective(Action):
        config = {"other": Other}

        def __init__(self) -> None:
            pass

        def identifier(self, other: Other) -> tuple[()]:
            return ()

        def perform(self, obj: Any, other: Other) -> None:
            other.touch()

    class MyApp(BaseApp):
        touched = False
        foo = directive(MyDirective)

    class SubApp(MyApp):
        touched = False

    @MyApp.foo()
    def f() -> None:
        pass

    assert not MyApp.touched

    commit(MyApp)

    # NOTE: mypy narrowing will make the code below unreachable
    if not TYPE_CHECKING:
        assert MyApp.touched

    assert not SubApp.touched

    commit(SubApp)

    assert SubApp.touched


def test_app_class_cleanup() -> None:
    class MyDirective(Action):
        config = {}

        app_class_arg = True

        def __init__(self) -> None:
            pass

        def identifier(self, app_class: type[MyApp]) -> tuple[()]:
            return ()

        def perform(self, obj: Any, app_class: type[MyApp]) -> None:
            app_class.touched.append(None)

    class MyApp(App):
        touched: list[None] = []

        @classmethod
        def clean(cls) -> None:
            cls.touched = []

        foo = directive(MyDirective)

    @MyApp.foo()
    def f() -> None:
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched == [None]

    commit(MyApp)

    assert MyApp.touched == [None]
