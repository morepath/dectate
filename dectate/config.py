import sys
import inspect
from .error import (
    ConflictError, DirectiveError, DirectiveReportError)
from .toposort import topological_sort
from .framehack import caller_package, get_frame_info


order_count = 0


class Configurable(object):
    """Object to which configuration actions apply.

    This object can be tucked away inside an App class.

    Actions are registered per configurable during the import phase. The
    minimal activity happens during this phase.

    During commit phase the configurable is executed. This expands any
    composite actions, groups actions into action groups and sorts
    them by depends so that they are executed in the correct order,
    and then executes each action group, which performs them.
    """
    def __init__(self, extends, testing_config):
        """
        :param extends:
          the configurables that this configurable extends.
        :type extends: list of configurables.
        :param testing_config:
          We can pass a config object used during testing. This causes
          the actions to be issued against the configurable directly
          instead of waiting for Venusian scanning. This allows
          the use of directive decorators in tests where scanning is
          not an option. Optional, default no testing config.
        """
        self.extends = extends
        self.testing_config = testing_config
        if testing_config:
            testing_config.configurable(self)
        # actions immediately registered with configurable
        self._actions = []

    def register_action(self, action, obj):
        global order_count
        action.order = order_count
        order_count += 1
        self._actions.append((action, obj))

    def group_actions(self):
        self._class_to_actions = d = {}

        # get the actions our actions extend
        for configurable in self.extends:
            for action_class in configurable.action_classes():
                if action_class not in d:
                    d[action_class] = Actions(
                        self.action_extends(action_class))

        # now add the actions for this configurable
        for action, obj in expand_actions(self._actions):
            action_class = action.group_class()
            actions = d.get(action_class)
            if actions is None:
                d[action_class] = actions = Actions(
                    self.action_extends(action_class))
            actions.add(action, obj)

    def action_extends(self, action_class):
        """Get actions for action class in extends.
        """
        return [
            configurable._class_to_actions.get(action_class, Actions([]))
            for configurable in self.extends]

    def action_classes(self):
        """Get action classes sorted in dependency order.
        """
        return sort_action_classes(self._class_to_actions.keys())

    def execute(self):
        """Execute actions for configurable.
        """
        self.group_actions()
        for action_class in self.action_classes():
            actions = self._class_to_actions.get(action_class)
            if actions is None:
                continue
            actions.execute(self)


class Actions(object):
    def __init__(self, extends):
        self._actions = []
        self._action_map = {}
        self.extends = extends

    def add(self, action, obj):
        self._actions.append((action, obj))

    def prepare(self, configurable):
        """Prepare.

        Detect any conflicts between actions.
        Merges in configuration of what this action extends.

        Prepare must be called before perform is called.
        """
        # check for conflicts and fill action map
        discriminators = {}
        self._action_map = action_map = {}

        for action, obj in self._actions:
            configurations = action.get_configurations(configurable)
            id = action.identifier(**configurations)
            discs = [id]
            discs.extend(action.discriminators(**configurations))
            for disc in discs:
                other_action = discriminators.get(disc)
                if other_action is not None:
                    raise ConflictError([action, other_action])
                discriminators[disc] = action
            action_map[id] = action, obj
        # inherit from extends
        for extend in self.extends:
            self.combine(extend)

    def combine(self, actions):
        """Combine another prepared actions with this one.

        Those configuration actions that would conflict are taken to
        have precedence over those being combined with this one. This
        allows the extending actions to override actions in
        extended actions.

        :param actions: the :class:`Actions` to combine with this one.
        """
        to_combine = actions._action_map.copy()
        to_combine.update(self._action_map)
        self._action_map = to_combine

    def execute(self, configurable):
        """Perform actions.
        """
        self.prepare(configurable)

        values = list(self._action_map.values())
        values.sort(key=lambda value: value[0].order or 0)

        if not values:
            return

        some_action, obj = values[0]
        group_class = some_action.group_class()
        kw = group_class.get_configurations(configurable)

        # run the group class before operation
        group_class.before(**kw)

        # perform the actual actions
        for action, obj in values:
            kw = action.get_configurations(configurable)
            try:
                action.log(configurable, obj)
                action.perform(obj, **kw)
            except DirectiveError as e:
                raise DirectiveReportError(u"{}".format(e), action)

        # run the group class after operation
        group_class.after(**kw)


class Action(object):
    """A configuration action.

    A configuration action is performed on an object and one or more
    configurations.

    Actions can conflict with each other based on their identifier and
    discriminators. Actions can override each other based on their
    identifier.

    Can be subclassed to implement concrete configuration actions.

    Actions classes also have a ``configurations`` attribute which is
    a dictionary mapping configuration name to configuration
    factory. When the directive is executed and no configuration with
    such a name yet exists, that configuration is created as an
    attribute of the Configurable. The configuration objects are passed
    into ``perform`` as keyword parameters.

    Action classes can have a ``depends`` attribute, which is a list
    of other action classes that need to be executed before this one
    is. Actions which depend on another will be executed after those
    actions are executed.
    """
    configurations = {}
    depends = []

    # the directive that was used gets stored on the instance
    directive = None

    def group_class(self):
        """By default we group directives by their class.

        Override this to group a directive with another directive,
        by returning that Directive class. It will create conflicts
        between those directives. Typically you'd do this when you are
        already subclassing from that directive too.

        The group class is also used to run to run any `before` and `after`
        methods that need to happen before or after all actions in a group
        run.
        """
        return self.__class__

    def frame_info(self):
        """Info about where in the source code the action was invoked.
        """
        if self.directive is None:
            return None
        return self.directive.frame_info

    @classmethod
    def get_configurations(cls, configurable):
        result = {}
        for name, factory in cls.configurations.items():
            configuration = getattr(configurable, name, None)
            if configuration is None:
                configuration = factory()
                setattr(configurable, name, configuration)
            result[name] = configuration
        return result

    def identifier(self, **kw):
        """Returns an immutable that uniquely identifies this config.

        :param **kw: a dictionary of configuration objects as specified
          by the configurations class attribute.

        Used for overrides and conflict detection.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def discriminators(self, **kw):
        """Returns a list of immutables to detect conflicts.

        :param **kw: a dictionary of configuration objects as specified
          by the configurations class attribute.

        Used for additional configuration conflict detection.
        """
        return []

    def perform(self, obj, **kw):
        """Register whatever is being configured with configurable.

        :param obj: the object that the action should be performed on.
        :param **kw: a dictionary of configuration objects as specified
          by the configurations class attribute.
        """
        raise NotImplementedError()

    @staticmethod
    def before(**kw):
        pass

    @staticmethod
    def after(**kw):
        pass

    # XXX for now don't log plain non-directive actions
    def log(self, configurable, obj):
        pass


class Composite(object):
    def actions(self, obj):
        return []


class Directive(object):
    """Created by the decorator.

    Can be used as a Python decorator.

    Can also be used as a context manager for a Python ``with``
    statement. This can be used to provide defaults for the directives
    used within the ``with`` statements context.

    When used as a decorator this tracks where in the source code
    the directive was used for the purposes of error reporting.
    """
    def __init__(self, app, action_factory, args, kw,
                 frame_info, directive_name, logger):
        """Initialize Directive.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action was configured.
        """
        self.app = app
        self.configurable = app.configurations
        self.action_factory = action_factory
        self.args = args
        self.kw = kw
        self.frame_info = frame_info
        self.directive_name = directive_name
        self.argument_info = (args, kw)
        self.logger = logger

    def action(self):
        result = self.action_factory(*self.args, **self.kw)
        # store the directive used on the action, useful for error reporting
        result.directive = self
        return result

    def __enter__(self):
        return DirectiveAbbreviation(self)

    def __exit__(self, type, value, tb):
        if tb is not None:
            return False

    def __call__(self, wrapped):
        """Call with function to decorate.
        """
        self.configurable.register_action(self.action(), wrapped)
        return wrapped

    def log(self, configurable, obj):
        if self.logger is None:
            return

        if configurable.app is not None:
            target_dotted_name = configurable.app.dotted_name()
            is_same = configurable.app is self.app
        else:
            target_dotted_name = repr(configurable)
            is_same = False

        if inspect.isfunction(obj):
            func_dotted_name = '%s.%s' % (obj.__module__, obj.__name__)
        else:
            func_dotted_name = repr(obj)

        if self.argument_info is not None:
            args, kw = self.argument_info
            arguments = ', '.join([repr(arg) for arg in args])
            if arguments:
                arguments += ', '
            arguments += ', '.join(['%s=%r' % (key, value) for key, value in
                                    sorted(kw.items())])
        else:
            assert False  # pragma: nocoverage

        message = '@%s.%s(%s) on %s' % (
            target_dotted_name, self.directive_name, arguments,
            func_dotted_name)

        if not is_same:
            message += ' (from %s)' % self.app.dotted_name()

        self.logger.debug(message)


class DirectiveAbbreviation(object):
    def __init__(self, directive):
        self.directive = directive

    def __call__(self, *args, **kw):
        frame = sys._getframe(1)
        frame_info = get_frame_info(frame)
        directive = self.directive

        combined_args = directive.args + args
        combined_kw = directive.kw.copy()
        combined_kw.update(kw)
        return Directive(
            app=directive.app,
            action_factory=directive.action_factory,
            args=combined_args,
            kw=combined_kw,
            frame_info=frame_info,
            directive_name=directive.directive_name,
            logger=directive.logger)


class Config(object):
    """Contains and executes configuration actions.

    Morepath configuration actions consist of decorator calls on
    :class:`App` instances, i.e. ``@App.view()`` and
    ``@App.path()``. The Config object can scan these configuration
    actions in a package. Once all required configuration is scanned,
    the configuration can be committed. The configuration is then
    processed, associated with :class:`morepath.config.Configurable`
    objects (i.e. :class:`App` objects), conflicts are detected,
    overrides applied, and the configuration becomes final.

    Once the configuration is committed all configured Morepath
    :class:`App` objects are ready to be served using WSGI.

    See :func:`setup`, which creates an instance with standard
    Morepath framework configuration. See also :func:`autoconfig` and
    :func:`autosetup` which help automatically load configuration from
    dependencies.
    """
    def __init__(self):
        self.configurables = []

    def scan(self, package=None, ignore=None, recursive=True,
             onerror=None):
        """Scan package for configuration actions (decorators).

        Register any found configuration actions with this
        object. This also includes finding any
        :class:`morepath.config.Configurable` objects.

        If given a package, it scans any modules and sub-packages as
        well recursively, unless `recursive` is `False`.

        :param package: The Python module or package to scan. Optional; if left
          empty case the calling package is scanned.
        :param ignore: A Venusian_ style ignore to ignore some modules during
          scanning. Optional. Defaults to ``['.test', '.tests']``.
        :param recursive: Scan packages recursively. By default this is
          ``True``. If set to ``False``, only the ``__init__.py`` of a package
          is scanned.
        :param onerror: onerror argument passed to Venusian's scan.
        """
        if package is None:
            package = caller_package()
        if ignore is None:
            ignore = ['.test', '.tests']
        scanner = venusian.Scanner(config=self)
        scanner.scan(package, ignore=ignore, recursive=recursive)

    def configurable(self, configurable):
        """Register a configurable with this config.

        This is normally not invoked directly, instead is called
        indirectly by :meth:`scan`.

        A :class:`App` object's configurations attribute is a configurable.

        :param: The :class:`morepath.config.Configurable` to register.
        """
        self.configurables.append(configurable)

    def commit(self):
        """Commit all configuration.

        * Clears any previous configuration from all registered
          :class:`morepath.config.Configurable` objects.
        * Prepares actions using :meth:`prepared`.
        * Actions are grouped by type of action (action class).
        * The action groups are executed in order of ``depends``
          between their action classes.
        * Per action group, configuration conflicts are detected.
        * Per action group, extending configuration is merged.
        * Finally all configuration actions are performed, completing
          the configuration process.

        This method should be called only once during the lifetime of
        a process, before the configuration is first used. After this
        the configuration is considered to be fixed and cannot be
        further modified. In tests this method can be executed
        multiple times as it automatically clears the
        configuration of its configurables first.
        """
        for configurable in sort_configurables(self.configurables):
            configurable.execute()


def sort_configurables(configurables):
    """Sort configurables topologically by extends.
    """
    return topological_sort(configurables, lambda c: c.extends)


def sort_action_classes(action_classes):
    """Sort action classes topologically by depends.
    """
    return topological_sort(action_classes, lambda c: c.depends)


def expand_actions(actions):
    for action, obj in actions:
        if isinstance(action, Composite):
            for sub_action, sub_obj in expand_actions(action.actions(obj)):
                yield sub_action, sub_obj
        else:
            if not hasattr(action, 'order'):
                global order_count
                action.order = order_count
                order_count += 1
            yield action, obj
