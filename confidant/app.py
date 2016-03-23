from functools import update_wrapper
import logging
import sys
from .config import Configurable, Directive
from .compat import with_metaclass
from .framehack import get_frame_info


class AppMeta(type):
    def __new__(cls, name, bases, d):
        testing_config = d.get('testing_config')
        extends = [base.configurations for base in bases
                   if hasattr(base, 'configurations')]
        d['configurations'] = Configurable(extends, testing_config)
        return super(AppMeta, cls).__new__(cls, name, bases, d)


class App(with_metaclass(AppMeta)):
    """A Morepath-based application object.
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
            frame_info = get_frame_info(frame)
            logger = logging.getLogger('morepath.directive.%s' %
                                       directive_name)
            return Directive(self, action_factory, args, kw,
                             frame_info, directive_name, logger)
        update_wrapper(method, action_factory.__init__)
        setattr(self.cls, self.name, classmethod(method))
        return action_factory
