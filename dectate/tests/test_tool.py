import pytest
from argparse import ArgumentTypeError

from dectate.config import Action, commit
from dectate.app import App
from dectate.tool import (parse_app_class, parse_directive, parse_filters,
                          convert_filters,
                          convert_dotted_name, convert_bool,
                          query_tool_output, query_app, ToolError)
from dectate import compat


def builtin_ref(s):
    if compat.PY3:
        return 'builtins.%s' % s
    else:
        return '__builtin__.%s' % s


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
    assert parse_directive(anapp.AnApp, 'unknown') is None


def test_parse_directive_not_a_directive():
    from dectate.tests.fixtures import anapp
    assert parse_directive(anapp.AnApp, 'known') is None


def test_parse_filters_main():
    assert parse_filters(['a=b', 'c = d', 'e=f ', ' g=h']) == {
        'a': 'b',
        'c': 'd',
        'e': 'f',
        'g': 'h'
    }


def test_parse_filters_error():
    with pytest.raises(ToolError):
        parse_filters(['a'])


def test_convert_filters_main():
    class MyAction(Action):
        filter_convert = {
            'model': convert_dotted_name
        }

    converted = convert_filters(
        MyAction,
        {'model': 'dectate.tests.fixtures.anapp.OtherClass'})
    assert len(converted) == 1
    from dectate.tests.fixtures.anapp import OtherClass
    assert converted['model'] is OtherClass


def test_convert_filters_default():
    class MyAction(Action):
        pass

    converted = convert_filters(
        MyAction,
        {"name": "foo"})
    assert len(converted) == 1
    assert converted['name'] == 'foo'


def test_convert_filters_error():
    class MyAction(Action):
        filter_convert = {
            'model': convert_dotted_name
        }

    with pytest.raises(ToolError):
        convert_filters(
            MyAction,
            {"model": "dectate.tests.fixtures.anapp.DoesntExist"})


def test_convert_filters_value_error():
    class MyAction(Action):
        filter_convert = {
            'count': int
        }

    assert convert_filters(MyAction, {"count": "3"}) == {'count': 3}

    with pytest.raises(ToolError):
        convert_filters(MyAction, {"count": "a"})


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

    l = list(query_tool_output([MyApp], 'foo', {'name': 'a'}))

    # we are not going to assert too much about the content of things
    # here as we probably want to tweak for a while, just assert that
    # we successfully produce output
    assert l


def test_query_tool_output_multiple_apps():
    class Base(App):
        pass

    class AlphaApp(Base):
        pass

    class BetaApp(Base):
        pass

    class GammaApp(Base):
        pass

    @Base.directive('foo')
    class FooAction(Action):
        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            pass

    @AlphaApp.foo('a')
    def f():
        pass

    @GammaApp.foo('b')
    def g():
        pass

    commit(AlphaApp, BetaApp, GammaApp)

    l = list(query_tool_output([AlphaApp, BetaApp, GammaApp], 'foo', {}))

    assert len(l) == 8


def test_query_app():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        filter_convert = {
            'count': int
        }

        def __init__(self, count):
            self.count = count

        def identifier(self):
            return self.count

        def perform(self, obj):
            pass

    @MyApp.foo(1)
    def f():
        pass

    @MyApp.foo(2)
    def g():
        pass

    commit(MyApp)

    l = list(query_app(MyApp, 'foo', count='1'))
    assert len(l) == 1
    assert l[0][0].count == 1


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
        list(query_tool_output([MyApp], 'foo', {'name': 'a'}))


def test_convert_bool():
    assert convert_bool('True')
    assert not convert_bool('False')
    with pytest.raises(ValueError):
        convert_bool('flurb')


def test_convert_dotted_name_builtin():
    assert convert_dotted_name(builtin_ref('int')) is int
    assert convert_dotted_name(builtin_ref('object')) is object


def test_app_without_directive():
    class MyApp(App):
        pass

    commit(MyApp)

    l = list(query_app(MyApp, 'foo', count='1'))
    assert l == []


def test_inheritance():
    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        filter_convert = {
            'count': int
        }

        def __init__(self, count):
            self.count = count

        def identifier(self):
            return self.count

        def perform(self, obj):
            pass

    @MyApp.foo(1)
    def f():
        pass

    @MyApp.foo(2)
    def g():
        pass

    commit(SubApp)

    l = list(query_app(SubApp, 'foo'))

    assert len(l) == 2
