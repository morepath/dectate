import logging
import sys
from .config import Configurable, Directive, commit, create_code_info
from .compat import with_metaclass


class Config(object):
    """The object that contains the configurations.

    The configurations are specified by the :attr:`Action.config`
    class attribute of :class:`Action`.
    """
    pass


class AppMeta(type):
    """Dectate metaclass.

    Sets up ``config`` and ``dectate`` class attributes.
    """
    def __new__(cls, name, bases, d):
        extends = [base.dectate for base in bases
                   if hasattr(base, 'dectate')]
        d['config'] = config = Config()
        d['dectate'] = configurable = Configurable(extends, config)
        result = super(AppMeta, cls).__new__(cls, name, bases, d)
        configurable.app_class = result
        return result


class App(with_metaclass(AppMeta)):
    """A configurable application object.

    Subclass this in your framework and add directives using
    the :meth:`App.directive` decorator.

    Set the ``logger_name`` class attribute to the logging prefix
    that Dectate should log to. By default it is ``"dectate.directive"``.
    """
    logger_name = 'dectate.directive'
    """The prefix to use for directive debug logging."""

    dectate = None
    """A dectate Configurable instance is installed here.

    This is installed when the class object is initialized, so during
    import-time when you use the ``class`` statement and subclass
    :class:`dectate.App`.

    This keeps tracks of the registrations done by using directives as long
    as committed configurations.
    """

    config = None
    """Config object that contains the configuration after commit.

    This is installed when the class object is initialized, so during
    import-time when you use the ``class`` statement and subclass
    :class:`dectate.App`, but is only filled after you commit the
    configuration.

    This keeps the final configuration result after commit. It is
    a very dumb object that has no methods and is just a container for
    attributes that contain the real configuration.
    """

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

        :param name: the name of the directive to register.
        :return: a directive that when called installs the directive
          method on the class.
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

        :param action_class: the :class:`dectate.Action` subclass to register.
        :return: the :class`dectate.Action` class that was registered.
        """
        cls.dectate.register_action_class(action_class)
        return action_class

    @classmethod
    def commit(cls):
        """Commit this class and any depending on it.

        This is intended to be overridden by subclasses if committing
        the class also commits other classes automatically, such as in
        the case in Morepath when one app is mounted into another. In
        such case it should return an iterable of all committed
        classes.

        :return: an iterable of committed classes
        """
        commit(cls)
        return [cls]

    @classmethod
    def is_committed(cls):
        """True if this app class was ever committed.

        :return: bool that is ``True`` when the app was committed before.
        """
        return cls.dectate.committed


class DirectiveDirective(object):
    """Implementation of the ``directive`` directive.

    :param cls: the class that this directive is registered on.
    :param name: the name of the directive.
    """
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name

    def __call__(self, action_factory):
        """Register the directive with app class.

        Creates a class method on the app class for the directive.

        :param action_factory: the :class:`dectate.Action` or
          :class:`dectate.Composite` subclass to register.
        :return: the action or composite subclass that was registered.
        """
        directive_name = self.name

        def method(cls, *args, **kw):
            frame = sys._getframe(1)
            code_info = create_code_info(frame)
            logger = logging.getLogger('%s.%s' %
                                       (cls.logger_name, directive_name))
            return Directive(cls, action_factory, args, kw,
                             code_info, directive_name, logger)
        method.action_factory = action_factory  # to help sphinxext
        setattr(self.cls, self.name, classmethod(method))
        method.__name__ = self.name
        # As of Python 3.5, the repr of bound methods uses __qualname__ instead
        # of __name__.  See http://bugs.python.org/issue21389#msg217566
        if hasattr(method, '__qualname__'):
            method.__qualname__ = type(self.cls).__name__ + '.' + self.name
        method.__doc__ = action_factory.__doc__
        method.__module__ = action_factory.__module__
        self.cls.dectate.register_action_class(action_factory)
        return action_factory
