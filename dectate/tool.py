from __future__ import print_function

import argparse
import inspect
from .query import Query, get_action_class
from .error import QueryError
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

    args, filters = parser.parse_known_args()

    if args.app:
        app_classes = args.app

    filters = parse_filters(filters)

    try:
        lines = list(query_tool_output(app_classes, args.directive,
                                       filters))
    except ToolError as e:
        parser.error(text_type(e))

    for line in lines:
        print(line)


def query_tool_output(app_classes, directive, filters):
    for app_class in app_classes:
        if not app_class.is_committed():
            raise ToolError("App %r was not committed." % app_class)

        actions = list(query_app(app_class, directive, **filters))

        if not actions:
            continue

        yield "App: %r" % app_class

        for action, obj in actions:
            if action.directive is None:
                continue  # XXX handle this case
            yield "  %s" % action.directive.code_info.filelineno()
            yield "  %s" % action.directive.code_info.sourceline
            yield ""


def query_app(app_class, directive, **filters):
    """Query a single app with raw filters.

    This function is especially useful for writing unit tests that
    test the conversion behavior.

    :param app_class: a :class:`App` subclass to query.
    :param directive: name of directive to query.
    :param ``**filters``: raw (unconverted) filter values.
    :return: iterable of ``action, obj`` tuples.
    """
    action_class = parse_directive(app_class, directive)
    if action_class is not None:
        filter_kw = convert_filters(action_class, filters)
        query = Query(action_class).filter(**filter_kw)
    else:
        query = Query()  # empty query
    return query(app_class)


def parse_directive(app_class, directive_name):
    try:
        return get_action_class(app_class, directive_name)
    except QueryError:
        return None


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
    """Convert input string to an object in a module.

    Takes a dotted name: ``pkg.module.attr`` gets ``attr``
    from module ``module`` which is in package ``pkg``.

    To refer to builtin objects such as ``int`` or ``object``, in
    Python 2 prefix with ``__builtin__.``, so ``__builtin__.int`` or
    ``__builtin__.None``. In Python 3 use ``builtins.`` as the prefix,
    so ``builtins.int`` and ``builtins.None``.

    Raises ``ValueError`` if it cannot be imported.

    """
    try:
        return resolve_dotted_name(s)
    except ImportError:
        raise ToolError("Cannot resolve dotted name: %s" % s)


def convert_bool(s):
    """Convert input string to boolean.

    Input string must either be ``True`` or ``False``.
    """
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError("Cannot convert bool: %r" % s)


def parse_filters(entries):
    result = {}
    for entry in entries:
        try:
            name, value = entry.split("=")
        except ValueError:
            raise ToolError("Cannot parse query filter, no =.")
        name = name.strip()
        result[name] = value.strip()
    return result


def convert_filters(action_class, filters):
    filter_convert = action_class.filter_convert

    result = {}

    for key, value in filters.items():
        parse = filter_convert.get(key, convert_default)
        try:
            result[key] = parse(value.strip())
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
