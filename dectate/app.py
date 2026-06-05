from __future__ import annotations

import sys
from functools import update_wrapper
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
)
from .config import Configurable, Directive, commit, create_code_info

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator
    from typing_extensions import Self
    from .config import Action, Composite, DirectiveAbbreviation
    from .types import DirectiveCallable

_T = TypeVar("_T")
_ActionT = TypeVar("_ActionT", bound="Action | Composite")
_AppT = TypeVar("_AppT", bound="App")
_P = ParamSpec("_P")


class Config:
    """The object that contains the configurations.

    The configurations are specified by the :attr:`Action.config`
    class attribute of :class:`Action`.
    """

    if TYPE_CHECKING:
        # NOTE: Since Config attributes are completely dynamic
        #       this is the best we can do.
        def __getattr__(self, name: str) -> Any:
            pass


class AppMeta(type):
    """Dectate metaclass.

    Sets up ``config`` and ``dectate`` class attributes.
    """

    def __new__(
        cls, name: str, bases: tuple[type[Any], ...], d: dict[str, Any]
    ) -> type[App]:
        extends = [base.dectate for base in bases if hasattr(base, "dectate")]
        d["config"] = config = Config()
        d["dectate"] = configurable = Configurable(extends, config)
        result = super().__new__(cls, name, bases, d)
        if TYPE_CHECKING:
            assert issubclass(result, App)
        configurable.app_class = result
        return result


class App(metaclass=AppMeta):
    """A configurable application object.

    Subclass this in your framework and add directives using
    the :meth:`App.directive` decorator.

    Set the ``logger_name`` class attribute to the logging prefix
    that Dectate should log to. By default it is ``"dectate.directive"``.
    """

    logger_name = "dectate.directive"
    """The prefix to use for directive debug logging."""

    dectate: Configurable
    """A dectate Configurable instance is installed here.

    This is installed when the class object is initialized, so during
    import-time when you use the ``class`` statement and subclass
    :class:`dectate.App`.

    This keeps tracks of the registrations done by using directives as long
    as committed configurations.
    """

    config: Config
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
    def get_directive_methods(
        cls,
    ) -> Iterator[tuple[str, DirectiveMethod[Self, ...]]]:
        for name in dir(cls):
            attr = getattr(cls, name)
            im_func = getattr(attr, "__func__", None)
            if im_func is None:
                continue
            if hasattr(im_func, "action_factory"):
                yield name, attr

    @classmethod
    def commit(cls) -> Collection[type[App]]:
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
    def is_committed(cls) -> bool:
        """True if this app class was ever committed.

        :return: bool that is ``True`` when the app was committed before.
        """
        return cls.dectate.committed

    @classmethod
    def clean(cls) -> None:
        """A method that sets or restores the state of the class.

        Normally Dectate only sets up configuration into the ``config``
        attribute, but in some cases you may touch other aspects of the
        class during configuration time. You can override this classmethod
        to set up the state of the class in its pristine condition.
        """
        pass


class BoundDirectiveMethod(Generic[_AppT, _P]):
    __name__: str
    __qualname__: str

    def __init__(
        self,
        cls: type[_AppT],
        func: DirectiveCallable[Concatenate[type[_AppT], _P]],
    ) -> None:
        self.__objclass__ = cls
        self.__func__ = func
        self.action_factory = func.action_factory
        update_wrapper(self, func)
        # remove forwarded partial, since we need to modify the params
        self.__dict__ = self.__dict__.copy()
        del self.__dict__["partial"]

    def partial(self, *args: Any, **kw: Any) -> DirectiveAbbreviation:
        return self.__func__.partial(self.__objclass__, *args, **kw)

    def __call__(self, *args: _P.args, **kw: _P.kwargs) -> Directive:
        return self.__func__(self.__objclass__, *args, **kw)

    def __repr__(self) -> str:
        return f"<bound method {self.__qualname__} of {self.__objclass__!r}>"


class DirectiveMethod(Generic[_AppT, _P]):
    __name__: str
    __qualname__: str

    def __init__(self, func: DirectiveCallable[Concatenate[Any, _P]]):
        self.__func__ = func
        update_wrapper(self, func)  # type: ignore[arg-type]

    def __get__(
        self, instance: _AppT | None, owner: type[_AppT], /
    ) -> DirectiveCallable[_P]:
        return BoundDirectiveMethod(owner, self.__func__)


def directive(
    # NOTE: Ideally this would be type[_ActionT] & Callable[_P, _ActionT]
    #       but until type intersections are a thing, this is the best
    #       trade-off, since we want to see an error if we provide incorrect
    #       arguments to a directive. Type checkers not catching that this
    #       needs to be a type instance, is the lesser evil.
    action_factory: Callable[_P, _ActionT],
) -> DirectiveMethod[Any, _P]:
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
    if not isinstance(action_factory, type):
        raise TypeError(
            "action_factory needs to be `dectate.Action` or `dectate.Composite` subclass."
        )

    def method(cls: Any, *args: _P.args, **kw: _P.kwargs) -> Directive:
        frame = sys._getframe(2)
        code_info = create_code_info(frame)
        return Directive(action_factory, code_info, cls, args, kw)

    def partial(cls: Any, *args: Any, **kw: Any) -> DirectiveAbbreviation:
        frame = sys._getframe(2)
        code_info = create_code_info(frame)
        directive = Directive(action_factory, code_info, cls, args, kw)
        with directive as abbreviation:
            return abbreviation

    # sphinxext and App.get_action_classes need to recognize this
    _method = cast("DirectiveCallable[Concatenate[Any, _P]]", method)
    _method.action_factory = action_factory
    _method.partial = partial  # type: ignore[method-assign]
    _method.__doc__ = action_factory.__doc__
    _method.__module__ = action_factory.__module__

    return DirectiveMethod(_method)
