from .config import Composite
from .error import QueryError


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
        to attribute name, by default they are the same.

        By default the keyword argument values are matched by equality,
        but you can override this using :attr:`Action.filter_compare`.

        Can be chained again with a new ``filter``.

        :param ``**kw``: keyword arguments to match against.
        :return: iterable of ``(action, obj)``.
        """
        return Filter(self, **kw)

    def attrs(self, *names):
        """Extract attributes from resulting actions.

        The list of attribute names indicates which keys to include
        in the dictionary. Obeys :attr:`Action.filter_name`.

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
      Can be instances of :class:`Action` or :class:`Composite`.
    """
    def __init__(self, *action_classes):
        self.action_classes = action_classes

    def execute(self, configurable):
        return query_action_classes(configurable, self.action_classes)


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


class NotFound(object):
    pass


NOT_FOUND = NotFound()


def compare_equality(compared, value):
    return compared == value


class Filter(Base):
    def __init__(self, query, **kw):
        self.query = query
        self.kw = kw

    def execute(self, configurable):
        for action, obj in self.query.execute(configurable):
            for name, value in self.kw.items():
                actual_name = action.filter_name.get(name, name)
                compared = getattr(action, actual_name, NOT_FOUND)
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
                actual_name = action.filter_name.get(name, name)
                attrs[name] = getattr(action, actual_name, NOT_FOUND)
            yield attrs


class Obj(Callable):
    def __init__(self, query):
        self.query = query

    def execute(self, configurable):
        for action, obj in self.query.execute(configurable):
            yield obj
