import venusian
from .compat import with_metaclass


class Registry(object):
    def __init__(self, testing_config):
        self.testing_config = testing_config


class AppMeta(type):
    def __new__(cls, name, bases, d):
        # XXX this code can be called with NewBase. investigate
        # newer six with_metaclass that fixes this.
        testing_config = d.get('confidant_testing_config')
        registry_factory = d.get('confidant_registry_factory')
        if registry_factory is None:
            # take the one from the first base class that has one
            for base in bases:
                if hasattr(base, 'confidant_registry_factory'):
                    registry_factory = base.confidant_registry_factory
                    break
        if registry_factory is not None:
            d['confidant_registry'] = registry_factory(testing_config)
        result = super(AppMeta, cls).__new__(cls, name, bases, d)
        venusian.attach(result, callback)
        return result


def callback(scanner, name, obj):
    scanner.config.appclass(obj)


class App(with_metaclass(AppMeta)):
    confidant_registry_factory = Registry
    confidant_testing_config = None
