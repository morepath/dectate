import venusian
from .toposort import topological_sort

class Configurable(object):
    def __init__(self, testing_config):
        self.testing_config = testing_config

    def clear(self):
        self.groups = {}

    def action(self, action):
        pass


class ActionGroup(object):
    def __init__(self, id):
        self.id = id
        self.actions = []


# this has the actual appclass that is going to be configured,
# not the appclass on which it was defined, which is the responsibility
# of the directive
class Action(object):
    def __init__(self, appclass, obj):
        self.appclass = appclass
        self.registry = appclass.registry
        self.obj = obj

    def group_id(self):
        return self.__class__

    def get_depends(self):
        return self.depends

    def identifier(self):
        raise NotImplementedError()

    def discriminators(self):
        return []

    def perform(self):
        raise NotImplementedError()

    def log(self):
        pass

# an action group determines conflicts
# 
class ActionGroup(object):
    pass

class Action(object):
    def __init__(self, depends):
        pass

    def group_key(self):
        return self.__class__

    
class Config(object):
    """Contains and executes configuration actions."""
    def __init__(self):
        self.appclasses = []
        self.actions = []

    def scan(self, package, categories=None, onerror=None, ignore=None):
        scanner = venusian.Scanner(config=self)
        scanner.scan(package, categories, onerror, ignore)

    def appclass(self, appclass):
        self.appclasses.append(cls)
        # XXX add additional actions?

    def action(self, action):
        self.actions.append(action)

    def commit(self):
        registries = self.get_sorted_registries()

        # clear old registries
        for registry in registries:
            registry.clear()

        # organize them by registry
        for action in self.actions:
            action.appclass.registry.action(action)

        # now perform the registries
        for registry in registries:
            registry.perform_actions()

    def get_sorted_registries(self):
        return [appclass.confidant_registry for appclass in
                topological_sort(self.appclasses, lambda cls: cls.__bases__)]
