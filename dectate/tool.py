from __future__ import print_function

import argparse
import inspect
from .query import Query, execute
from .app import App


class ToolError(Exception):
    pass


def querytool(directive_app_class, app_classes):
    parser = argparse.ArgumentParser(description="Query Dectate actions")
    parser.add_argument('--app', help="Dotted name for App subclass.",
                        type=parse_app_class, action='append')
    parser.add_argument('directive', help="Name of the directive.")

    args, query = parser.parse_known_args()

    try:
        action_class = parse_directive(directive_app_class, args.directive)
    except ToolError as e:
        parser.error(e.value)

    filter_kw = parse_filter(action_class, query)

    if args.app:
        app_classes = args.app

    query = Query(action_class).filter(**filter_kw)

    for app_class in app_classes:
        print("App: %r" % app_class)
        for action, obj in execute(app_class, query):
            if action.directive is None:
                continue  # XXX handle this case
            print(action.directive.code_info.filelineno())
            print(action.directive.code_info.sourceline)
            print()
        print()


def parse_directive(app_class, directive_name):
    directive_method = getattr(app_class, directive_name, None)
    if directive_method is None:
        raise ToolError("No directive exists on %r with name: %s" %
                        (app_class, directive_name))
    action_class = getattr(directive_method, 'action_factory', None)
    if action_class is None:
        raise ToolError("%r on %r is not a directive" %
                        (directive_name, app_class))
    return action_class


def parse_app_class(s):
    try:
        app_class = resolve_dotted_name(s)
    except ImportError:
        raise argparse.ArgumentTypeError(
            "Cannot resolve dotted name: %r" % s)
    if not inspect.isclass(app_class):
        raise argparse.ArgumentTypeError(
            "%r is not a class" % s)
    if not issubclass(app_class, App):
        raise argparse.ArgumentTypeError(
            "%r is not a subclass of dectate.App" % s)
    return app_class


def parse_filter(action_class, entries):
    result = {}

    for entry in entries:
        name, value = entry.split("=")
        name = name.strip()
        value = value.strip()
        result[name] = value

    return result


def resolve_dotted_name(name, module=None):
    """Adapted from zope.dottedname
    """
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError("relative name without base module")
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name

    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found
