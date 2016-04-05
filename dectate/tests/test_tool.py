import pytest
from argparse import ArgumentTypeError

from dectate.tool import parse_app_class, parse_directive, ToolError


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
