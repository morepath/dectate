from __future__ import print_function


import argparse
import inspect
from .query import Query, execute
from .app import App
from .config import Action


def querytool():
    # XXX factor various parsing logics out into separate functions
    # that can be tested
    parser = argparse.ArgumentParser(description="Query Dectate actions")
    parser.add_argument('app_class', help="Dotted name for App subclass.",
                        type=parse_app_class)
    parser.add_argument('directive', help="Name of the directive.")

    args, query = parser.parse_known_args()

    directive_name = args.directive

    app_class = args.app_class

    directive_method = getattr(app_class, directive_name, None)
    if directive_method is None:
        parser.error("No directive exists with name: %s" % directive_name)
    action_class = getattr(directive_method, 'action_factory', None)
    if action_class is None:
        parser.error("No directive exists with name: %s" % directive_name)
    if not issubclass(action_class, Action):
        parser.error("No directive exists with name: %s" % directive_name)

    filter_kw = {}

    for entry in query:
        name, value = entry.split("=")
        name = name.strip()
        value = value.strip()
        filter_kw[name] = value

    for action, obj in execute(app_class,
                               Query(action_class).filter(**filter_kw)):
        if action.directive is None:
            continue  # XXX handle this case
        print(action.directive.code_info.filelineno())
        print(action.directive.code_info.sourceline)
        print()


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
