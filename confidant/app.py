from functools import update_wrapper
import logging
import sys
from .config import Configurable, Directive
from .compat import with_metaclass
from .framehack import get_frame_info


class Registry(Configurable):
    """A registry holding an application's configuration.
    """
    app = None  # app this registry belongs to. set later during scanning

    def __init__(self, name, bases, testing_config):
        self.name = name
        bases = [base.registry for base in bases if hasattr(base, 'registry')]
        Configurable.__init__(self, bases, testing_config)

    def actions(self):
        return []


class AppMeta(type):
    def __new__(cls, name, bases, d):
        testing_config = d.get('testing_config')
        d['registry'] = Registry(name, bases, testing_config)
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

    def __call__(self, directive):
        directive_name = self.name

        def method(self, *args, **kw):
            frame = sys._getframe(1)
            frame_info = get_frame_info(frame)
            argument_info = args, kw
            logger = logging.getLogger('morepath.directive.%s' %
                                       directive_name)
            return directive(self, frame_info,
                             directive_name, argument_info, logger,
                             *args, **kw)

        # this is to help morepath.sphinxext to do the right thing
        method.actual_directive = directive
        update_wrapper(method, directive.__init__)
        setattr(self.cls, self.name, classmethod(method))
        return directive
