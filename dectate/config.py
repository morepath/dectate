import sys
import inspect
from .error import (
    ConflictError, ConfigError, DirectiveError, DirectiveReportError)
from .toposort import topological_sort


order_count = 0


class Configurable(object):
    """Object to which configuration actions apply.

    This object is normally tucked away as the ``dectate`` class
    attribute on an :class:`dectate.App` subclass.

    Actions are registered per configurable during the import phase;
    actions are not actually created or performed, so their
    ``__init__`` and ``perform`` are not yet called.

    During the commit phase the configurable is executed. This expands
    any composite actions, groups actions into action groups and sorts
    them by depends so that they are executed in the correct order,
    and then executes each action group, which performs them.
    """
    app_class = None

    def __init__(self, extends, config):
        """
       :param extends:
          the configurables that this configurable extends.
        :type extends: list of configurables.
        :param config:
          the object that will contains the actual configuration.
          Normally it's the ``config`` class attribute of the
          :class:`dectate.App` subclass.
        """
        self.extends = extends
        self.config = config
        # all action classes known
        self._action_classes = set()
        # directives used with configurable
        self._directives = []

    def register_action_class(self, action_class):
        """Register an action class with this configurable.

        Called during import time when the :meth:`App.directive` directive
        is executed.
        """
        self._action_classes.add(action_class)

    def register_directive(self, directive, obj):
        """Register a directive with this configurable.

        Called during import time when directives are used.
        """
        self._directives.append((directive, obj))

    def setup(self):
        """Set up config object and action groups.

        This happens during the start of the commit phase.

        Takes inheritance of apps into account.
        """
        # add any action classes defined by base classes
        s = self._action_classes
        for configurable in self.extends:
            for action_class in configurable._action_classes:
                if action_class not in s:
                    s.add(action_class)

        # we want to have use group_class for each true Action class
        action_classes = set()
        for action_class in s:
            if not issubclass(action_class, Action):
                continue
            group_class = action_class.group_class
            if group_class is None:
                group_class = action_class
            else:
                if group_class.group_class is not None:
                    raise ConfigError(
                        "Cannot use group_class on another action class "
                        "that uses group_class: %r" % action_class)
                if 'config' in action_class.__dict__:
                    raise ConfigError(
                        "Cannot use config class attribute when you use "
                        "group_class: %r" % action_class)
                if 'before' in action_class.__dict__:
                    raise ConfigError(
                        "Cannot define before method when you use "
                        "group_class: %r" % action_class)
                if 'after' in action_class.__dict__:
                    raise ConfigError(
                        "Cannot define after method when you use "
                        "group_class: %r" % action_class)
            action_classes.add(group_class)

        # delete any old configuration in case we run this a second time
        for action_class in sort_action_classes(action_classes):
            delete_config(action_class, self)

        # now we create ActionGroup objects for each action class group
        self._action_groups = d = {}
        for action_class in sort_action_classes(action_classes):
            setup_config(action_class, self)
            d[action_class] = ActionGroup(action_class,
                                          self.action_extends(action_class))

    def group_actions(self):
        """Groups actions for this configurable into action groups.
        """
        # turn directives into actions
        actions = [(directive.action(), obj)
                   for (directive, obj) in self._directives]

        # add the actions for this configurable to the action group
        d = self._action_groups

        for action, obj in expand_actions(actions):
            action_class = action.group_class
            if action_class is None:
                action_class = action.__class__
            d[action_class].add(action, obj)

    def action_extends(self, action_class):
        """Get ActionGroup for all action classes in ``extends``.
        """
        return [
            configurable._action_groups.get(action_class,
                                            ActionGroup(action_class, []))
            for configurable in self.extends]

    def execute(self):
        """Execute actions for configurable.
        """
        self.setup()
        self.group_actions()
        for action_class in sort_action_classes(self._action_groups.keys()):
            self._action_groups[action_class].execute(self)


class ActionGroup(object):
    """A group of actions.

    Grouped actions are all performed together.

    Normally actions are grouped by their class, but actions can also
    indicate another action class to group with using ``group_class``.
    """
    def __init__(self, action_class, extends):
        """
        :param action_class:
          the action_class that identifies this action group.
        :param extends:
          list of action groups extended by this action group.
        """
        self.action_class = action_class
        self._actions = []
        self._action_map = {}
        self.extends = extends

    def add(self, action, obj):
        """Add an action and the object this action is to be performed on.

        :param action: an :class:`Action` instance.
        :param obj: the function or class the action should be performed for.
        """
        self._actions.append((action, obj))

    def prepare(self, configurable):
        """Prepare the action group for a configurable.

        Detect any conflicts between actions.
        Merges in configuration of what this action extends.

        :param configurable: The :class:`Configurable` option to prepare for.
        """
        # check for conflicts and fill action map
        discriminators = {}
        self._action_map = action_map = {}

        for action, obj in self._actions:
            kw = action._get_config_kw(configurable)
            id = action.identifier(**kw)
            discs = [id]
            discs.extend(action.discriminators(**kw))
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

        :param actions: list of :class:`ActionGroup` objects to
          combine with this one.
        """
        to_combine = actions._action_map.copy()
        to_combine.update(self._action_map)
        self._action_map = to_combine

    def execute(self, configurable):
        """Perform actions for configurable.

        :param configurable: the :class:`Configurable` instance to execute
          the actions against.
        """
        self.prepare(configurable)

        actions = list(self._action_map.values())
        actions.sort(key=lambda value: value[0].order or 0)

        kw = self.action_class._get_config_kw(configurable)

        # run the group class before operation
        self.action_class.before(**kw)

        # perform the actual actions
        for action, obj in actions:
            try:
                action._log(configurable, obj)
                action.perform(obj, **kw)
            except DirectiveError as e:
                raise DirectiveReportError(u"{}".format(e),
                                           action.code_info)

        # run the group class after operation
        self.action_class.after(**kw)


class Action(object):
    """A configuration action.

    Base class of configuration actions.

    A configuration action is performed for an object (typically a
    function or a class object) and affects one or more configuration
    objects.

    Actions can conflict with each other based on their identifier and
    discriminators. Actions can override each other based on their
    identifier. Actions can only be in conflict with actions of the
    same action class or actions with the same ``action_group``.
    """
    config = {}
    """Describe configuration.

    A dict mapping configuration names to factory functions. The
    resulting configuration objects are passed into
    :meth:`Action.identifier`, :meth:`Action.discriminators`,
    :meth:`Action.perform`, and :meth:`Action.before` and
    :meth:`Action.after`.

    After commit completes, the configured objects are found
    as attributes on :class:`App.config`.
    """

    depends = []
    """List of other action classes to be executed before this one.

    The ``depends`` class attribute contains a list of other action
    classes that need to be executed before this one is. Actions which
    depend on another will be executed after those actions are
    executed.

    Omit if you don't care about the order.
    """

    group_class = None
    """Action class to group with.

    This class attribute can be supplied with the class of another
    action that this action should be grouped with. Only actions in
    the same group can be in conflict. Actions in the same group share
    the ``config`` and ``before`` and ``after`` of the action class
    indicated by ``group_class``.

    By default an action only groups with others of its same class.
    """

    # the directive that was used gets stored on the instance
    directive = None

    # this is here to make update_wrapper work even when an __init__
    # is not provided by the subclass
    def __init__(self):
        pass

    @property
    def code_info(self):
        """Info about where in the source code the action was invoked.

        Is an instance of :class:`CodeInfo`.

        Can be ``None`` if action does not have an associated directive
        but was created manually.
        """
        if self.directive is None:
            return None
        return self.directive.code_info

    def _log(self, configurable, obj):
        """Log this directive for configurable given configured obj.
        """
        if self.directive is None:
            return
        self.directive.log(configurable, obj)

    @classmethod
    def _get_config_kw(cls, configurable):
        """Get the config objects set up for this configurable into a dict.

        This dict can then be passed as keyword parameters (using ``**``)
        into the relevant methods such as :meth:`Action.perform`.
        """
        result = {}
        config = configurable.config
        group_class = cls.group_class
        if group_class is None:
            group_class = cls
        for name, factory in group_class.config.items():
            result[name] = getattr(config, name)
        return result

    def identifier(self, **kw):
        """Returns an immutable that uniquely identifies this config.

        Needs to be implemented by the :class:`Action` subclass.

        Used for overrides and conflict detection.

        If two actions in the same group have the same identifier in
        the same configurable, those two actions are in conflict and a
        :class:`ConflictError` is raised during :func:`commit`.

        If an action in an extending configurable has the same
        identifier as the configurable being extended, that action
        overrides the original one in the extending configurable.

        :param ``**kw``: a dictionary of configuration objects as specified
          by the ``config`` class attribute.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def discriminators(self, **kw):
        """Returns a list of immutables to detect conflicts.

        Can be implemented by the :class:`Action` subclass.

        Used for additional configuration conflict detection.

        :param ``**kw``: a dictionary of configuration objects as specified
          by the ``config`` class attribute.
        """
        return []

    def perform(self, obj, **kw):
        """Do whatever configuration is needed for ``obj``.

        Needs to be implemented by the :class:`Action` subclass.

        Raise a :exc:`DirectiveError` to indicate that the action
        cannot be performed due to incorrect configuration.

        :param obj: the object that the action should be performed
          for. Typically a function or a class object.
        :param ``**kw``: a dictionary of configuration objects as specified
          by the ``config`` class attribute.
        """
        raise NotImplementedError()

    @staticmethod
    def before(**kw):
        """Do setup just before actions in a group are performed.

        Can be implemented as a static method by the :class:`Action`
        subclass.

        :param ``**kw``: a dictionary of configuration objects as specified
          by the ``config`` class attribute.
        """
        pass

    @staticmethod
    def after(**kw):
        """Do setup just after actions in a group are performed.

        Can be implemented as a static method by the :class:`Action`
        subclass.

        :param ``**kw``: a dictionary of configuration objects as specified
          by the ``config`` class attribute.
        """
        pass


class Composite(object):
    """A composite configuration action.

    Base class of composite actions.

    Composite actions are very simple: implement the ``action``
    method and return a iterable of actions in there.
    """

    # this is here to make update_wrapper work even when an __init__
    # is not provided by the subclass
    def __init__(self):
        pass

    @property
    def code_info(self):
        """Info about where in the source code the action was invoked.

        Is an instance of :class:`CodeInfo`.

        Can be ``None`` if action does not have an associated directive
        but was created manually.
        """
        if self.directive is None:
            return None
        return self.directive.code_info

    def actions(self, obj):
        """Specify a iterable of actions to perform for ``obj``.

        The iteratable should yield ``action``, ``obj`` tuples,
        where ``action`` is instance of
        class :class:`Action` or :class:`Composite` and ``obj``
        is the object to perform the action with.

        Needs to be implemented by the :class:`Composite` subclass.
        """
        raise NotImplementedError


class Directive(object):
    """Decorator to use for configuration.

    Can also be used as a context manager for a Python ``with``
    statement. This can be used to provide defaults for the directives
    used within the ``with`` statements context.

    When used as a decorator this tracks where in the source code
    the directive was used for the purposes of error reporting.
    """
    def __init__(self, app_class, action_factory, args, kw,
                 code_info, directive_name, logger):
        """
        :param app_class: the :class:`dectate.App` subclass that this
          directive is used on.
        :param action_factory: function that constructs an action instance.
        :args: the positional arguments passed into the directive.
        :kw: the keyword arguments passed into the directive.
        :code_info: a :class:`CodeInfo` instance describing where this
          directive was invoked.
        :directive_name: the name of this directive.
        :logger: the logger object to use.
        """
        self.app_class = app_class
        self.configurable = app_class.dectate
        self.action_factory = action_factory
        self.args = args
        self.kw = kw
        self.code_info = code_info
        self.directive_name = directive_name
        self.argument_info = (args, kw)
        self.logger = logger

    def action(self):
        """Get the :class:`Action` instance represented by this directive.
        """
        try:
            result = self.action_factory(*self.args, **self.kw)
        except TypeError as e:
            raise DirectiveReportError(u"{}".format(e), self.code_info)

        # store the directive used on the action, useful for error reporting
        result.directive = self
        return result

    def __enter__(self):
        return DirectiveAbbreviation(self)

    def __exit__(self, type, value, tb):
        if tb is not None:
            return False

    def __call__(self, wrapped):
        """Call with function or class to decorate.

        The decorated object is returned unchanged.
        """
        self.configurable.register_directive(self, wrapped)
        return wrapped

    def log(self, configurable, obj):
        """Log this directive.

        :configurable: the configurable that this directive is logged for.
        :obj: the function or class object to that this directive is used
          on.
        """
        if self.logger is None:
            return

        target_dotted_name = dotted_name(configurable.app_class)
        is_same = self.app_class is configurable.app_class

        if inspect.isfunction(obj):
            func_dotted_name = '%s.%s' % (obj.__module__, obj.__name__)
        else:
            func_dotted_name = repr(obj)

        args, kw = self.argument_info
        arguments = ', '.join([repr(arg) for arg in args])

        if kw:
            if arguments:
                arguments += ', '
            arguments += ', '.join(
                ['%s=%r' % (key, value) for key, value in
                 sorted(kw.items())])

        message = '@%s.%s(%s) on %s' % (
            target_dotted_name, self.directive_name, arguments,
            func_dotted_name)

        if not is_same:
            message += ' (from %s)' % dotted_name(self.app_class)

        self.logger.debug(message)


class DirectiveAbbreviation(object):
    """An abbreviated directive to be used with the ``with`` statement.
    """
    def __init__(self, directive):
        self.directive = directive

    def __call__(self, *args, **kw):
        """Combine the args and kw from the directive with supplied ones.
        """
        frame = sys._getframe(1)
        code_info = create_code_info(frame)
        directive = self.directive

        combined_args = directive.args + args
        combined_kw = directive.kw.copy()
        combined_kw.update(kw)
        return Directive(
            app_class=directive.app_class,
            action_factory=directive.action_factory,
            args=combined_args,
            kw=combined_kw,
            code_info=code_info,
            directive_name=directive.directive_name,
            logger=directive.logger)


def commit(apps):
    """Commit an iterable of app classes

    A commit causes the configuration actions to be performed. The
    resulting configuration information is stored under the
    ``.config`` class attribute of each :class:`App` subclass
    supplied.

    This function may safely be invoked multiple times -- each time
    the known configuration is recommitted.

    :param apps: an iterable of :class:`App` classes to perform
      configuration actions on.
    """
    configurables_from_apps = []
    for c in apps:
        if isinstance(c, Configurable):
            configurables_from_apps.append(c)
        else:
            configurables_from_apps.append(c.dectate)

    for configurable in sort_configurables(configurables_from_apps):
        configurable.execute()


def sort_configurables(configurables):
    """Sort configurables topologically by ``extends``.

    :param configurables: an iterable of configurables to sort.
    :return: a topologically sorted list of configurables.
    """
    return topological_sort(configurables, lambda c: c.extends)


def sort_action_classes(action_classes):
    """Sort action classes topologically by depends.

    :param action_classes: iterable of :class:`Action` subclasses
      class objects.
    :return: a topologically sorted list of action_classes.
    """
    return topological_sort(action_classes, lambda c: c.depends)


def expand_actions(actions):
    """Expand any :class:`Composite` instances into :class:`Action` instances.

    Expansion is recursive; composites that return composites are expanded
    again.

    :param actions: an iterable of :class:`Composite` and :class:`Action`
      instances.
    :return: an iterable of :class:`Action` instances.
    """
    for action, obj in actions:
        if isinstance(action, Composite):
            # make sure all sub actions propagate originating directive
            # info
            try:
                sub_actions = []
                for sub_action, sub_obj in action.actions(obj):
                    sub_action.directive = action.directive
                    sub_actions.append((sub_action, sub_obj))
            except DirectiveError as e:
                raise DirectiveReportError(u"{}".format(e),
                                           action.code_info)
            for sub_action, sub_obj in expand_actions(sub_actions):
                yield sub_action, sub_obj
        else:
            if not hasattr(action, 'order'):
                global order_count
                action.order = order_count
                order_count += 1
            yield action, obj


class CodeInfo(object):
    """Information about where code was invoked.

    The ``path`` attribute gives the path to the Python module that the
    code was invoked in.

    The ``lineno`` attribute gives the linenumber in that file.

    The ``sourceline`` attribute contains the actual source line that
    did the invocation.
    """
    def __init__(self, path, lineno, sourceline):
        self.path = path
        self.lineno = lineno
        self.sourceline = sourceline


def create_code_info(frame):
    """Return code information about a frame.

    Returns a :class:`CodeInfo` instance.
    """
    frameinfo = inspect.getframeinfo(frame)

    try:
        sourceline = frameinfo.code_context[0].strip()
    except:  # pragma NO COVER
        # dont understand circumstance here, 3rdparty code without comment
        sourceline = frameinfo.code_context

    return CodeInfo(
        path=frameinfo.filename,
        lineno=frameinfo.lineno,
        sourceline=sourceline)


def factory_key(item):
    name, factory = item
    arguments = getattr(factory, 'factory_arguments', None)
    if arguments is None:
        return []
    return arguments.items()


def get_factory_arguments(action, config, factory):
    arguments = getattr(factory, 'factory_arguments', None)
    if arguments is None:
        return {}
    result = {}
    for name in arguments.keys():
        value = getattr(config, name, None)
        if value is None:
            raise ConfigError(
                ("Cannot find factory argument %r for "
                 "factory %r in action class %r") %
                (name, factory, action))
        result[name] = getattr(config, name, None)
    return result


def setup_config(action, configurable):
    """Set up the config objects on the ``config`` attribute.
    """
    # sort the items in order of creation
    items = topological_sort(action.config.items(), factory_key)

    config = configurable.config
    for name, factory in items:
        if name not in action.config:
            # topological sort introduces all dependencies, but
            # we only want to construct those we have in actual config
            continue
        # if we already have this set up, we don't want to create
        # it anew
        configured = getattr(config, name, None)
        if configured is not None:
            setattr(config, name, configured)
            continue
        kw = get_factory_arguments(action, config, factory)
        setattr(config, name, factory(**kw))


def delete_config(action, configurable):
    """Delete config objects on the ``config`` attribute.
    """
    config = configurable.config
    for name in action.config.keys():
        if hasattr(config, name):
            delattr(config, name)


def dotted_name(cls):
    return '%s.%s' % (cls.__module__, cls.__name__)
