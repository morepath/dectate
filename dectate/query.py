from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar
from .config import Composite
from .error import QueryError

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from .app import App
    from .config import Action, Configurable


_T_co = TypeVar("_T_co", covariant=True)


class Callable(Generic[_T_co]):
    def __call__(self, app_class: type[App] | App) -> Iterable[_T_co]:
        """Execute the query against an app class.

        :param app_class: a :class:`App` subclass to execute the query
        against.
        :return: iterable of ``(action, obj)`, where ``action`` is a
        :class:`Action` instance and `obj` is the function or class
        that was decorated.
        """
        return self.execute(app_class.dectate)

    # NOTE: forward declare required subclass method
    def execute(self, configurable: Configurable) -> Iterable[_T_co]:
        raise NotImplementedError


class Base(Callable[tuple["Action", Any]]):
    def filter(self, **kw: Any) -> Filter:
        """Filter this query by keyword arguments.

        The keyword arguments are matched with attributes on the
        action. :attr:`Action.filter_name` is used to map keyword name
        to attribute name, by default they are the
        same. :meth:`Action.filter_get_value` can also be implemented
        for more complicated attribute access as a fallback.

        By default the keyword argument values are matched by equality,
        but you can override this using :attr:`Action.filter_compare`.

        Can be chained again with a new ``filter``.

        :param ``**kw``: keyword arguments to match against.
        :return: iterable of ``(action, obj)``.

        """
        return Filter(self, **kw)

    def attrs(self, *names: str) -> Attrs:
        """Extract attributes from resulting actions.

        The list of attribute names indicates which keys to include in
        the dictionary. Obeys :attr:`Action.filter_name` and
        :attr:`Action.filter_get_value`.

        :param: ``*names``: list of names to extract.
        :return: iterable of dictionaries.

        """
        return Attrs(self, names)

    def obj(self) -> Obj:
        """Get objects from results.

        Throws away actions in the results and return an iterable of objects.

        :return: iterable of decorated objects.
        """
        return Obj(self)


class Query(Base):
    """An object representing a query.

    A query can be chained with :meth:`Query.filter`, :meth:`Query.attrs`,
    :meth:`Query.obj`.

    :param: ``*action_classes``: one or more action classes to query for.
      Can be instances of :class:`Action` or :class:`Composite`. Can
      also be strings indicating directive names, in which case they
      are looked up on the app class before execution.
    """

    def __init__(self, *action_classes: type[Action | Composite] | str) -> None:
        self.action_classes = action_classes

    def execute(
        self, configurable: Configurable
    ) -> Iterator[tuple[Action, Any]]:
        app_class = configurable.app_class
        assert app_class is not None
        action_classes = []
        for action_class in self.action_classes:
            if isinstance(action_class, str):
                action_class = get_action_class(app_class, action_class)
            action_classes.append(action_class)
        return query_action_classes(configurable, action_classes)


def expand_action_classes(
    action_classes: Iterable[type[Action | Composite]],
) -> set[type[Action]]:
    result = set()
    for action_class in action_classes:
        if issubclass(action_class, Composite):
            query_classes = action_class.query_classes
            if not query_classes:
                raise QueryError(
                    "Query of composite action %r but no "
                    "query_classes defined." % action_class
                )
            for query_class in expand_action_classes(query_classes):
                result.add(query_class)
        else:
            group_class = action_class.group_class
            if group_class is None:
                result.add(action_class)
            else:
                result.add(group_class)
    return result


def query_action_classes(
    configurable: Configurable,
    action_classes: Iterable[type[Action | Composite]],
) -> Iterator[tuple[Action, Any]]:
    for action_class in expand_action_classes(action_classes):
        action_group = configurable.get_action_group(action_class)
        if action_group is None:
            raise QueryError(
                "%r is not an action of %r"
                % (action_class, configurable.app_class)
            )
        yield from action_group.get_actions()


def get_action_class(
    app_class: type[App] | App, directive_name: str
) -> type[Action | Composite]:
    directive_method = getattr(app_class, directive_name, None)
    if directive_method is None:
        raise QueryError(
            "No directive exists on %r with name: %s"
            % (app_class, directive_name)
        )
    action_class = getattr(directive_method, "action_factory", None)
    if action_class is None:
        raise QueryError(
            f"{directive_name!r} on {app_class!r} is not a directive"
        )
    return action_class  # type: ignore[no-any-return]


def compare_equality(compared: object, value: object) -> bool:
    return compared == value


class Filter(Base):
    def __init__(self, query: Base, **kw: Any) -> None:
        self.query = query
        self.kw = kw

    def execute(
        self, configurable: Configurable
    ) -> Iterator[tuple[Action, Any]]:
        for action, obj in self.query.execute(configurable):
            for name, value in sorted(self.kw.items()):
                compared = action.get_value_for_filter(name)
                compare_func = action.filter_compare.get(name, compare_equality)
                if not compare_func(compared, value):
                    break
            else:
                yield action, obj


class Attrs(Callable[dict[str, Any]]):
    def __init__(self, query: Base, names: Sequence[str]) -> None:
        self.query = query
        self.names = names

    def execute(self, configurable: Configurable) -> Iterator[dict[str, Any]]:
        for action, obj in self.query.execute(configurable):
            attrs = {}
            for name in self.names:
                attrs[name] = action.get_value_for_filter(name)
            yield attrs


class Obj(Callable[Any]):
    def __init__(self, query: Base) -> None:
        self.query = query

    def execute(self, configurable: Configurable) -> Iterator[Any]:
        for action, obj in self.query.execute(configurable):
            yield obj
