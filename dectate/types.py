from __future__ import annotations

from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar

if TYPE_CHECKING:
    from .app import App
    from .config import Action, Composite, Directive, DirectiveAbbreviation


_AppT = TypeVar("_AppT", bound="App")
_P = ParamSpec("_P")


class DirectiveCallable(Protocol[_P]):
    __name__: str
    __qualname__: str
    action_factory: type[Action | Composite]

    def partial(self, *args: Any, **kwargs: Any) -> DirectiveAbbreviation:
        raise NotImplementedError

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> Directive:
        raise NotImplementedError
