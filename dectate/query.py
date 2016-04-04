import inspect


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
    def __init__(self, action_class):
        self.action_class = action_class

    def __call__(self, configurable):
        action_group = configurable._action_groups.get(self.action_class, None)
        for action, obj in action_group._actions:
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
