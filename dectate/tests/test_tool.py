import pytest
from argparse import ArgumentTypeError

from dectate.config import Action, commit
from dectate.app import App
from dectate.tool import (parse_app_class, parse_directive, parse_filter,
                          convert_dotted_name, query_tool_output, ToolError)


def test_parse_app_class_main():
    from dectate.tests.fixtures import anapp

    app_class = parse_app_class(
        'dectate.tests.fixtures.anapp.AnApp')
    assert app_class is anapp.AnApp


def test_parse_app_class_cannot_import():
    with pytest.raises(ArgumentTypeError):
        parse_app_class(
            'dectate.tests.fixtures.nothere.AnApp')


def test_parse_app_class_not_a_class():
    with pytest.raises(ArgumentTypeError):
        parse_app_class('dectate.tests.fixtures.anapp.other')


def test_parse_app_class_no_app_class():
    with pytest.raises(ArgumentTypeError):
        parse_app_class('dectate.tests.fixtures.anapp.OtherClass')


def test_parse_directive_main():
    from dectate.tests.fixtures import anapp

    action_class = parse_directive(anapp.AnApp, 'foo')
    assert action_class is anapp.FooAction


def test_parse_directive_no_attribute():
    from dectate.tests.fixtures import anapp
    with pytest.raises(ToolError):
        parse_directive(anapp.AnApp, 'unknown')


def test_parse_directive_not_a_directive():
    from dectate.tests.fixtures import anapp
    with pytest.raises(ToolError):
        parse_directive(anapp.AnApp, 'known')


def test_parse_filter_main():
    class MyAction(Action):
        filter_convert = {
            'model': convert_dotted_name
        }

    converted = parse_filter(
        MyAction,
        ["model=dectate.tests.fixtures.anapp.OtherClass"])
    assert len(converted) == 1
    from dectate.tests.fixtures.anapp import OtherClass
    assert converted['model'] is OtherClass


def test_parse_filter_default():
    class MyAction(Action):
        pass

    converted = parse_filter(
        MyAction,
        ["name=foo"])
    assert len(converted) == 1
    assert converted['name'] == 'foo'


def test_parse_filter_convert_error():
    class MyAction(Action):
        filter_convert = {
            'model': convert_dotted_name
        }

    with pytest.raises(ToolError):
        parse_filter(
            MyAction,
            ["model=dectate.tests.fixtures.anapp.DoesntExist"])


def test_parse_filter_value_error():
    class MyAction(Action):
        filter_convert = {
            'count': int
        }

    assert parse_filter(MyAction, ["count=3"]) == {'count': 3}

    with pytest.raises(ToolError):
        parse_filter(MyAction, ["count=a"])


def test_query_tool_output():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            pass

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    l = list(query_tool_output([MyApp], 'foo', ['name=a']))

    # we are not going to assert too much about the content of things
    # here as we probably want to tweak for a while, just assert that
    # we successfully produce output
    assert l


def test_query_tool_uncommitted():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            pass

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    with pytest.raises(ToolError):
        list(query_tool_output([MyApp], 'foo', ['name=a']))
