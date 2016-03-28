import sys
import inspect
from .error import (
    ConflictError, DirectiveError, DirectiveReportError)
from .toposort import topological_sort


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
    app_class = None

    def __init__(self, extends, config):
        """
        :param extends:
          the configurables that this configurable extends.
        :type extends: list of configurables.
        """
        self.extends = extends
        self.config = config
        # all action classes known
        self._action_classes = set()
        # directives used with configurable
        self._directives = []

    def register_action_class(self, action_factory):
        self._action_classes.add(action_factory)

    def register_directive(self, directive, obj):
        self._directives.append((directive, obj))

    def setup(self):
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
            action_classes.add(group_class)

        # nowe we create ActionGroup objects for each action class group
        self._action_groups = d = {}
        for action_class in sort_action_classes(action_classes):
            action_class.setup_config(self)
            d[action_class] = ActionGroup(action_class,
                                          self.action_extends(action_class))

    def group_actions(self):
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
        """Get actions for action class in extends.
        """
        return [
            configurable._action_groups.get(action_class,
                                            ActionGroup(action_class, []))
            for configurable in self.extends]

    def action_classes(self):
        """Get action classes sorted in dependency order.
        """
        return sort_action_classes(self._action_groups.keys())

    def execute(self):
        """Execute actions for configurable.
        """
        self.setup()
        self.group_actions()
        for action_class in self.action_classes():
            self._action_groups[action_class].execute(self)


class ActionGroup(object):
    def __init__(self, action_class, extends):
        self.action_class = action_class
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

        actions = list(self._action_map.values())
        actions.sort(key=lambda value: value[0].order or 0)

        kw = self.action_class.get_configurations(configurable)

        # run the group class before operation
        self.action_class.before(**kw)

        # perform the actual actions
        for action, obj in actions:
            kw = action.get_configurations(configurable)
            try:
                action.log(configurable, obj)
                action.perform(obj, **kw)
            except DirectiveError as e:
                raise DirectiveReportError(u"{}".format(e), action)

        # run the group class after operation
        self.action_class.after(**kw)


class Action(object):
    """A configuration action.

    A configuration action is performed on an object and one or more
    configurations.

    Actions can conflict with each other based on their identifier and
    discriminators. Actions can override each other based on their
    identifier.

    Can be subclassed to implement concrete configuration actions.

    Actions classes also have a ``config`` attribute which is
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
    config = {}
    depends = []
    group_class = None

    # the directive that was used gets stored on the instance
    directive = None

    def code_info(self):
        """Info about where in the source code the action was invoked.
        """
        if self.directive is None:
            return None
        return self.directive.code_info

    def log(self, configurable, obj):
        if self.directive is None:
            return
        self.directive.log(configurable, obj)

    @classmethod
    def setup_config(cls, configurable):
        config = configurable.config
        for name, factory in cls.config.items():
            c = getattr(config, name, None)
            if c is None:
                c = factory()
                setattr(config, name, c)

    @classmethod
    def get_configurations(cls, configurable):
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

        :param **kw: a dictionary of configuration objects as specified
          by the configurations class attribute.

        Used for overrides and conflict detection.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def discriminators(self, **kw):
        """Returns a list of immutables to detect conflicts.

        :param **kw: a dictionary of configuration objects as specified
          by the config class attribute.

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
    def __init__(self, app_class, action_factory, args, kw,
                 code_info, directive_name, logger):
        """Initialize Directive.

        :param configurable: :class:`morepath.config.Configurable` object
          for which this action was configured.
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
        self.configurable.register_directive(self, wrapped)
        return wrapped

    def log(self, configurable, obj):
        if self.logger is None:
            return

        target_dotted_name = configurable.app_class.dotted_name()
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
            message += ' (from %s)' % self.app_class.dotted_name()

        self.logger.debug(message)


class DirectiveAbbreviation(object):
    def __init__(self, directive):
        self.directive = directive

    def __call__(self, *args, **kw):
        frame = sys._getframe(1)
        code_info = get_code_info(frame)
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


def commit(configurables):
    configurables_from_apps = []
    for c in configurables:
        if isinstance(c, Configurable):
            configurables_from_apps.append(c)
        else:
            configurables_from_apps.append(c.dectate)

    for configurable in sort_configurables(configurables_from_apps):
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


class CodeInfo(object):
    """FrameInfo object.
    """
    def __init__(self, path, lineno, sourceline):
        self.path = path
        self.lineno = lineno
        self.sourceline = sourceline


def get_code_info(frame):
    """Return code information about a frame.
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
