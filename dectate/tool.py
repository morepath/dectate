from __future__ import annotations

import argparse
import inspect
from typing import TYPE_CHECKING, Any

from .app import App
from .error import QueryError
from .query import Query, get_action_class

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from .config import Action, Composite
    from .query import Filter


class ToolError(Exception):
    pass


def query_tool(app_classes: Iterable[type[App]]) -> None:
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
    parser.add_argument(
        "--app",
        help="Dotted name for App subclass.",
        type=parse_app_class,
        action="append",
    )
    parser.add_argument("directive", help="Name of the directive.")

    args, raw_filters = parser.parse_known_args()

    if args.app:
        app_classes = args.app

    filters = parse_filters(raw_filters)

    try:
        lines = list(query_tool_output(app_classes, args.directive, filters))
    except ToolError as e:
        parser.error(str(e))

    for line in lines:
        print(line)


def query_tool_output(
    app_classes: Iterable[type[App]], directive: str, filters: dict[str, str]
) -> Iterator[str]:
    for app_class in app_classes:
        if not app_class.is_committed():
            msg = f"App {app_class!r} was not committed."
            raise ToolError(msg)

        actions = list(query_app(app_class, directive, **filters))

        if not actions:
            continue

        yield f"App: {app_class!r}"

        for action, _obj in actions:
            if action.directive is None:
                continue  # pragma: no cover  # XXX handle this case
            yield f"  {action.directive.code_info.filelineno()}"
            yield f"  {action.directive.code_info.sourceline}"
            yield ""


def query_app(
    app_class: type[App], directive: str, **filters: Any
) -> Iterable[tuple[Action, Any]]:
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
        query: Query | Filter = Query(action_class).filter(**filter_kw)
    else:
        query = Query()  # empty query
    return query(app_class)


def parse_directive(
    app_class: type[App], directive_name: str
) -> type[Action | Composite] | None:
    try:
        return get_action_class(app_class, directive_name)
    except QueryError:
        return None


def parse_app_class(s: str) -> type[App]:
    try:
        app_class = resolve_dotted_name(s)
    except ImportError:
        msg = f"Cannot resolve dotted name: {s!r}"
        raise argparse.ArgumentTypeError(msg)
    if not inspect.isclass(app_class):
        msg = f"{s!r} is not a class"
        raise argparse.ArgumentTypeError(msg)
    if not issubclass(app_class, App):
        msg = f"{s!r} is not a subclass of dectate.App"
        raise argparse.ArgumentTypeError(msg)
    return app_class


def convert_default(s: str) -> str:
    return s


def convert_dotted_name(s: str) -> Any:
    """Convert input string to an object in a module.

    Takes a dotted name: ``pkg.module.attr`` gets ``attr``
    from module ``module`` which is in package ``pkg``.

    To refer to builtin objects such as ``int`` or ``object``
    prefix them with ``builtins.``, so ``builtins.int`` or
    ``builtins.None``.

    Raises ``ValueError`` if it cannot be imported.

    """
    try:
        return resolve_dotted_name(s)
    except ImportError:
        msg = f"Cannot resolve dotted name: {s}"
        raise ToolError(msg)


def convert_bool(s: str) -> bool:
    """Convert input string to boolean.

    Input string must either be ``True`` or ``False``.
    """
    if s == "True":
        return True
    if s == "False":
        return False
    msg = f"Cannot convert bool: {s!r}"
    raise ValueError(msg)


def parse_filters(entries: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        try:
            name, value = entry.split("=")
        except ValueError:
            msg = "Cannot parse query filter, no =."
            raise ToolError(msg)
        name = name.strip()
        result[name] = value.strip()
    return result


def convert_filters(
    action_class: type[Action | Composite], filters: dict[str, str]
) -> dict[str, Any]:
    filter_convert = action_class.filter_convert

    result: dict[str, Any] = {}

    for key, value in filters.items():
        parse = filter_convert.get(key, convert_default)
        try:
            result[key] = parse(value.strip())
        except ValueError as e:
            raise ToolError(str(e))

    return result


def resolve_dotted_name(name: str, module: str | None = None) -> Any:
    """Adapted from zope.dottedname."""
    name_parts = name.split(".")
    if not name_parts[0]:
        if module is None:
            msg = "relative name without base module"
            raise ValueError(msg)
        module_parts = module.split(".")
        name_parts.pop(0)
        if TYPE_CHECKING:
            # NOTE: Undo mypy narrowing to Literal[""] for name_parts[0]
            name_parts = name_parts
        while not name_parts[0]:
            module_parts.pop()
            name_parts.pop(0)
        name_parts = module_parts + name_parts

    used = name_parts.pop(0)
    found = __import__(used)
    for n in name_parts:
        used += "." + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found
