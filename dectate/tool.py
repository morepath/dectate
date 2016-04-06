from __future__ import print_function

import argparse
import inspect
from .query import Query
from .app import App
from .compat import text_type


class ToolError(Exception):
    pass


def query_tool(app_classes):
    """Command-line query tool for dectate.

    Uses command-line arguments to do the query and prints the results.

    usage: decq [-h] [--app APP] directive <filter>

    Query all directives named ``foo`` in given app classes::

      $ decq foo

    Query directives ``foo`` with ``name`` attribute set to ``alpha``::

      $ decq foo name=alpha

    Query directives ``foo`` specifically in given app::

      $ decq --app=myproject.App foo

    :param app_classes: a list of :class:`App` subclasses to query by default.
    """
    parser = argparse.ArgumentParser(description="Query Dectate actions")
    parser.add_argument('--app', help="Dotted name for App subclass.",
                        type=parse_app_class, action='append')
    parser.add_argument('directive', help="Name of the directive.")

    args, filter_entries = parser.parse_known_args()

    if args.app:
        app_classes = args.app

    try:
        lines = list(query_tool_output(app_classes, args.directive,
                                       filter_entries))
    except ToolError as e:
        parser.error(text_type(e))

    for line in lines:
        print(line)


def query_tool_output(app_classes, directive, filter_entries):
    for app_class in app_classes:
        if not app_class.dectate.commited:
            raise ToolError("App %r was not committed." % app_class)

        yield "App: %r" % app_class

        action_class = parse_directive(app_class, directive)
        filter_kw = parse_filter(action_class, filter_entries)
        query = Query(action_class).filter(**filter_kw)

        actions = list(query(app_class))

        if not actions:
            yield "  Nothing found"
            return

        for action, obj in actions:
            if action.directive is None:
                continue  # XXX handle this case
            yield "  %s" % action.directive.code_info.filelineno()
            yield "  %s" % action.directive.code_info.sourceline
            yield ""


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


def convert_default(s):
    return s


def convert_dotted_name(s):
    try:
        return resolve_dotted_name(s)
    except ImportError:
        raise ToolError("Cannot resolve dotted name: %s" % s)


def parse_filter(action_class, entries):
    filter_convert = action_class.filter_convert

    result = {}

    for entry in entries:
        name, value = entry.split("=")
        name = name.strip()
        parse = filter_convert.get(name, convert_default)
        try:
            result[name] = parse(value.strip())
        except ValueError as e:
            raise ToolError(text_type(e))
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
