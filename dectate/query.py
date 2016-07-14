from .config import Composite
from .error import QueryError
from .compat import string_types


class Callable(object):
    def __call__(self, app_class):
        """Execute the query against an app class.

        :param app_class: a :class:`App` subclass to execute the query
        against.
        :return: iterable of ``(action, obj)`, where ``action`` is a
        :class:`Action` instance and `obj` is the function or class
        that was decorated.
        """
        return self.execute(app_class.dectate)


class Base(Callable):
    def filter(self, **kw):
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

    def attrs(self, *names):
        """Extract attributes from resulting actions.

        The list of attribute names indicates which keys to include in
        the dictionary. Obeys :attr:`Action.filter_name` and
        :attr:`Action.filter_get_value`.

        :param: ``*names``: list of names to extract.
        :return: iterable of dictionaries.

        """
        return Attrs(self, names)

    def obj(self):
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
    def __init__(self, *action_classes):
        self.action_classes = action_classes

    def execute(self, configurable):
        app_class = configurable.app_class
        action_classes = []
        for action_class in self.action_classes:
            if isinstance(action_class, string_types):
                action_class = get_action_class(app_class, action_class)
            action_classes.append(action_class)
        return query_action_classes(configurable, action_classes)


def expand_action_classes(action_classes):
    result = set()
    for action_class in action_classes:
        if issubclass(action_class, Composite):
            query_classes = action_class.query_classes
            if not query_classes:
                raise QueryError(
                    "Query of composite action %r but no "
                    "query_classes defined." % action_class)
            for query_class in expand_action_classes(query_classes):
                result.add(query_class)
        else:
            group_class = action_class.group_class
            if group_class is None:
                result.add(action_class)
            else:
                result.add(group_class)
    return result


def query_action_classes(configurable, action_classes):
    for action_class in expand_action_classes(action_classes):
        action_group = configurable.get_action_group(action_class)
        if action_group is None:
            raise QueryError("%r is not an action of %r" %
                             (action_class, configurable.app_class))
        for action, obj in action_group.get_actions():
            yield action, obj


def get_action_class(app_class, directive_name):
    directive_method = getattr(app_class, directive_name, None)
    if directive_method is None:
        raise QueryError("No directive exists on %r with name: %s" %
                         (app_class, directive_name))
    action_class = getattr(directive_method, 'action_factory', None)
    if action_class is None:
        raise QueryError("%r on %r is not a directive" %
                         (directive_name, app_class))
    return action_class


def compare_equality(compared, value):
    return compared == value


class Filter(Base):
    def __init__(self, query, **kw):
        self.query = query
        self.kw = kw

    def execute(self, configurable):
        for action, obj in self.query.execute(configurable):
            for name, value in sorted(self.kw.items()):
                compared = action.get_value_for_filter(name)
                compare_func = action.filter_compare.get(
                    name, compare_equality)
                if not compare_func(compared, value):
                    break
            else:
                yield action, obj


class Attrs(Callable):
    def __init__(self, query, names):
        self.query = query
        self.names = names

    def execute(self, configurable):
        for action, obj in self.query.execute(configurable):
            attrs = {}
            for name in self.names:
                attrs[name] = action.get_value_for_filter(name)
            yield attrs


class Obj(Callable):
    def __init__(self, query):
        self.query = query

    def execute(self, configurable):
        for action, obj in self.query.execute(configurable):
            yield obj
