from __future__ import annotations

import pytest
from argparse import ArgumentTypeError
from typing import Any

from dectate.config import Action, commit
from dectate.app import App, directive
from dectate.tool import (
    parse_app_class,
    parse_directive,
    parse_filters,
    convert_filters,
    convert_dotted_name,
    convert_bool,
    query_tool_output,
    query_app,
    ToolError,
)


def test_parse_app_class_main() -> None:
    from dectate.tests.fixtures import anapp

    app_class = parse_app_class("dectate.tests.fixtures.anapp.AnApp")
    assert app_class is anapp.AnApp


def test_parse_app_class_cannot_import() -> None:
    with pytest.raises(ArgumentTypeError):
        parse_app_class("dectate.tests.fixtures.nothere.AnApp")


def test_parse_app_class_not_a_class() -> None:
    with pytest.raises(ArgumentTypeError):
        parse_app_class("dectate.tests.fixtures.anapp.other")


def test_parse_app_class_no_app_class() -> None:
    with pytest.raises(ArgumentTypeError):
        parse_app_class("dectate.tests.fixtures.anapp.OtherClass")


def test_parse_directive_main() -> None:
    from dectate.tests.fixtures import anapp

    action_class = parse_directive(anapp.AnApp, "foo")
    assert action_class is anapp.FooAction


def test_parse_directive_no_attribute() -> None:
    from dectate.tests.fixtures import anapp

    assert parse_directive(anapp.AnApp, "unknown") is None


def test_parse_directive_not_a_directive() -> None:
    from dectate.tests.fixtures import anapp

    assert parse_directive(anapp.AnApp, "known") is None


def test_parse_filters_main() -> None:
    assert parse_filters(["a=b", "c = d", "e=f ", " g=h"]) == {
        "a": "b",
        "c": "d",
        "e": "f",
        "g": "h",
    }


def test_parse_filters_error() -> None:
    with pytest.raises(ToolError):
        parse_filters(["a"])


def test_convert_filters_main() -> None:
    class MyAction(Action):
        filter_convert = {"model": convert_dotted_name}

    converted = convert_filters(
        MyAction, {"model": "dectate.tests.fixtures.anapp.OtherClass"}
    )
    assert len(converted) == 1
    from dectate.tests.fixtures.anapp import OtherClass

    assert converted["model"] is OtherClass


def test_convert_filters_default() -> None:
    class MyAction(Action):
        pass

    converted = convert_filters(MyAction, {"name": "foo"})
    assert len(converted) == 1
    assert converted["name"] == "foo"


def test_convert_filters_error() -> None:
    class MyAction(Action):
        filter_convert = {"model": convert_dotted_name}

    with pytest.raises(ToolError):
        convert_filters(
            MyAction, {"model": "dectate.tests.fixtures.anapp.DoesntExist"}
        )


def test_convert_filters_value_error() -> None:
    class MyAction(Action):
        filter_convert = {"count": int}

    assert convert_filters(MyAction, {"count": "3"}) == {"count": 3}

    with pytest.raises(ToolError):
        convert_filters(MyAction, {"count": "a"})


def test_query_tool_output() -> None:
    class FooAction(Action):
        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> None:
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo("a")
    def f() -> None:
        pass

    @MyApp.foo("b")
    def g() -> None:
        pass

    commit(MyApp)

    li = list(query_tool_output([MyApp], "foo", {"name": "a"}))

    # we are not going to assert too much about the content of things
    # here as we probably want to tweak for a while, just assert that
    # we successfully produce output
    assert li


def test_query_tool_output_multiple_apps() -> None:
    class FooAction(Action):
        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> None:
            pass

    class Base(App):
        foo = directive(FooAction)

    class AlphaApp(Base):
        pass

    class BetaApp(Base):
        pass

    class GammaApp(Base):
        pass

    @AlphaApp.foo("a")
    def f() -> None:
        pass

    @GammaApp.foo("b")
    def g() -> None:
        pass

    commit(AlphaApp, BetaApp, GammaApp)

    li = list(query_tool_output([AlphaApp, BetaApp, GammaApp], "foo", {}))

    assert len(li) == 8


def test_query_app() -> None:
    class FooAction(Action):
        filter_convert = {"count": int}

        def __init__(self, count: int) -> None:
            self.count = count

        def identifier(self) -> int:
            return self.count

        def perform(self, obj: Any) -> None:
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo(1)
    def f() -> None:
        pass

    @MyApp.foo(2)
    def g() -> None:
        pass

    commit(MyApp)

    li = list(query_app(MyApp, "foo", count="1"))
    assert len(li) == 1
    assert isinstance(li[0][0], FooAction)
    assert li[0][0].count == 1


def test_query_tool_uncommitted() -> None:
    class FooAction(Action):
        def __init__(self, name: str) -> None:
            self.name = name

        def identifier(self) -> str:
            return self.name

        def perform(self, obj: Any) -> None:
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo("a")
    def f() -> None:
        pass

    @MyApp.foo("b")
    def g() -> None:
        pass

    with pytest.raises(ToolError):
        list(query_tool_output([MyApp], "foo", {"name": "a"}))


def test_convert_bool() -> None:
    assert convert_bool("True")
    assert not convert_bool("False")
    with pytest.raises(ValueError):
        convert_bool("flurb")


def test_convert_dotted_name_builtin() -> None:
    assert convert_dotted_name("builtins.int") is int
    assert convert_dotted_name("builtins.object") is object


def test_app_without_directive() -> None:
    class MyApp(App):
        pass

    commit(MyApp)

    li = list(query_app(MyApp, "foo", count="1"))
    assert li == []


def test_inheritance() -> None:
    class FooAction(Action):
        filter_convert = {"count": int}

        def __init__(self, count: int) -> None:
            self.count = count

        def identifier(self) -> int:
            return self.count

        def perform(self, obj: Any) -> None:
            pass

    class MyApp(App):
        foo = directive(FooAction)

    class SubApp(MyApp):
        pass

    @MyApp.foo(1)
    def f() -> None:
        pass

    @MyApp.foo(2)
    def g() -> None:
        pass

    commit(SubApp)

    li = list(query_app(SubApp, "foo"))

    assert len(li) == 2
