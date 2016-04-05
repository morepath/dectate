import inspect
from .config import Composite
from .error import QueryError


def execute(app_class, query):
    configurable = app_class.dectate
    return query(configurable)


class Base(object):
    def filter(self, **kw):
        return Filter(self, **kw)

    def attrs(self, *names):
        return Attrs(self, names)

    def obj(self):
        return Obj(self)


class Query(Base):
    def __init__(self, *action_classes):
        self.action_classes = action_classes

    def __call__(self, configurable):
        return query_action_classes(configurable, self.action_classes)


def query_action_classes(configurable, action_classes):
    for action_class in action_classes:
        if issubclass(action_class, Composite):
            query_classes = action_class.query_classes
            if not query_classes:
                raise QueryError(
                    "Query of composite action %r but no "
                    "query_classes defined." % action_class)
            for action, obj in query_action_classes(
                    configurable, query_classes):
                yield action, obj
        else:
            action_group = configurable.get_action_group(action_class)
            for action, obj in action_group.get_actions():
                yield action, obj


class NotFound(object):
    pass


NOT_FOUND = NotFound()


class Filter(Base):
    def __init__(self, query, **kw):
        self.query = query
        self.kw = kw

    def __call__(self, configurable):
        for action, obj in self.query(configurable):
            match = True
            for name, value in self.kw.items():
                actual_name = action.query_names.get(name, name)
                compared = getattr(action, actual_name, NOT_FOUND)
                if inspect.isclass(value):
                    if not issubclass(compared, value):
                        match = False
                elif compared != value:
                    match = False
            if match:
                yield action, obj


class Attrs(object):
    def __init__(self, query, names):
        self.query = query
        self.names = names

    def __call__(self, configurable):
        for action, obj in self.query(configurable):
            attrs = {}
            for name in self.names:
                actual_name = action.query_names.get(name, name)
                attrs[name] = getattr(action, actual_name, NOT_FOUND)
            yield attrs


class Obj(object):
    def __init__(self, query):
        self.query = query

    def __call__(self, configurable):
        for action, obj in self.query(configurable):
            yield obj
