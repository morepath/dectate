from functools import update_wrapper
import logging
import sys
from .config import Configurable, Directive, commit, get_code_info
from .compat import with_metaclass

global_configurables = []


class Config(object):
    """The object that contains the configurations.

    The configurations are specified by the :attr:`Action.config`
    class attribute of :class:`Action`.
    """
    pass


class AppMeta(type):
    """Dectate metaclass.

    Sets up ``config`` and ``dectate`` class attributes.

    Keeps track of all :class:`App` subclasses.
    """
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
    """Automatically commit all :class:`App` subclasses.

    Dectate keeps track of all :class:`App` subclasses that have
    been imported. You can automatically commit configuration for
    all of them.
    """
    commit(global_configurables)


class App(with_metaclass(AppMeta)):
    """A configurable application object.

    Subclass this in your framework and add directives using
    the :meth:`App.directive` decorator.

    Set the ``logger_name`` class attribute to the logging prefix
    that Dectate should log to. By default it is ``"dectate.directive"``.
    """
    logger_name = 'dectate.directive'
    """The prefix to use for directive debug logging."""

    @classmethod
    def directive(cls, name):
        """Decorator to register a new directive with this application class.

        You use this as a class decorator for a
        :class:`dectate.Action` or a :class:`dectate.Composite`
        subclass::

           @MyApp.directive('my_directive')
           class FooAction(dectate.Action):
               ...

        This needs to be executed *before* the directive is used and
        thus might introduce import dependency issues unlike normal
        Dectate configuration, so beware! An easy way to make sure
        that all directives are installed before you use them is to
        make sure you define them in the same module as where you
        define the :class:`App` subclass that has them.

        """
        return DirectiveDirective(cls, name)

    @classmethod
    def private_action_class(cls, action_class):
        """Register a private action class.

        In some cases action classes can be an implementation detail,
        for instance in the implementation of a Composite action.

        In this case you don't want the action class to be known
        but not have a directive.

        This function may be used as a decorator like this::

          @App.private_action_class
          class MyActionClass(dectate.Action):
              ...
        """
        cls.dectate.register_action_class(action_class)
        return action_class


class DirectiveDirective(object):
    """Implementation of the ``directive`` directive.
    """
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name

    def __call__(self, action_factory):
        directive_name = self.name

        def method(self, *args, **kw):
            frame = sys._getframe(1)
            code_info = get_code_info(frame)
            logger = logging.getLogger('%s.%s' %
                                       (self.logger_name, directive_name))
            return Directive(self, action_factory, args, kw,
                             code_info, directive_name, logger)
        method.action_factory = action_factory  # to help sphinxext
        update_wrapper(method, action_factory.__init__)
        setattr(self.cls, self.name, classmethod(method))
        self.cls.dectate.register_action_class(action_factory)
        return action_factory
