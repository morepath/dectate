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
    def get_directive_methods(cls):
        for name in dir(cls):
            attr = getattr(cls, name)
            im_func = getattr(attr, '__func__', None)
            if im_func is None:
                continue
            if hasattr(im_func, 'action_factory'):
                yield name, attr

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

    @classmethod
    def clean(cls):
        """A method that sets or restores the state of the class.

        Normally Dectate only sets up configuration into the ``config``
        attribute, but in some cases you may touch other aspects of the
        class during configuration time. You can override this classmethod
        to set up the state of the class in its pristine condition.
        """
        pass


def directive(action_factory):
    """Create a classmethod to hook action to application class.

    You pass in a :class:`dectate.Action` or a
    :class:`dectate.Composite` subclass and can attach the result as a
    class method to an :class:`dectate.App` subclass::

      class FooAction(dectate.Action):
          ...

      class MyApp(dectate.App):
          my_directive = dectate.directive(MyAction)

    Alternatively you can also define the direction inline using
    this as a decorator::

      class MyApp(dectate.App):
          @directive
          class my_directive(dectate.Action):
              ...

    :param action_factory: an action class to use as the directive.
    :return: a class method that represents the directive.
    """
    def method(cls, *args, **kw):
        frame = sys._getframe(1)
        code_info = create_code_info(frame)
        return Directive(action_factory, code_info, cls, args, kw)
    # sphinxext and App.get_action_classes need to recognize this
    method.action_factory = action_factory
    method.__doc__ = action_factory.__doc__
    method.__module__ = action_factory.__module__
    return classmethod(method)
