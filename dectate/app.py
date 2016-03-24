from functools import update_wrapper
import logging
import sys
from .config import Configurable, Directive, commit, get_code_info
from .compat import with_metaclass

global_configurables = []


class Config(object):
    pass


class AppMeta(type):
    def __new__(cls, name, bases, d):
        extends = [base.dectate for base in bases
                   if hasattr(base, 'dectate')]
        d['config'] = config = Config()
        d['dectate'] = configurable = Configurable(extends, config)
        global_configurables.append(configurable)
        result = super(AppMeta, cls).__new__(cls, name, bases, d)
        configurable.app_class = result
        return result


def autocommit():
    commit(global_configurables)


class App(with_metaclass(AppMeta)):
    """A configurable application object.
    """
    testing_config = None

    @classmethod
    def directive(cls, name):
        """Decorator to register a new directive with this application class.

        You use this as a class decorator for a :class:`morepath.Directive`
        subclass::

           @App.directive('my_directive')
           class FooDirective(morepath.Directive):
               ...

        This needs to be executed *before* the directive is being used
        and thus might introduce import dependency issues unlike
        normal Morepath configuration, so beware! An easy way to make
        sure that all directives are installed before you use them is
        to make sure you define them in the same module as where you
        define the application class that has them.
        """
        return DirectiveDirective(cls, name)

    @classmethod
    def dotted_name(cls):
        return '%s.%s' % (cls.__module__, cls.__name__)


class DirectiveDirective(object):
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name

    def __call__(self, action_factory):
        directive_name = self.name

        def method(self, *args, **kw):
            frame = sys._getframe(1)
            code_info = get_code_info(frame)
            logger = logging.getLogger('dectate.directive.%s' %
                                       directive_name)
            return Directive(self, action_factory, args, kw,
                             code_info, directive_name, logger)
        update_wrapper(method, action_factory.__init__)
        setattr(self.cls, self.name, classmethod(method))
        return action_factory
