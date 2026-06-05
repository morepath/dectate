from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dectate.config import Action, CodeInfo


class ConfigError(Exception):
    """Raised when configuration is bad."""


def conflict_keyfunc(action: Action) -> tuple[str, int]:
    code_info = action.code_info
    if code_info is None:
        return ("", 0)
    return (code_info.path, code_info.lineno)


class ConflictError(ConfigError):
    """Raised when there is a conflict in configuration.

    Describes where in the code directives are in conflict.
    """

    def __init__(self, actions: list[Action]) -> None:
        actions.sort(key=conflict_keyfunc)
        self.actions = actions
        result = ["Conflict between:"]
        for action in actions:
            code_info = action.code_info
            if code_info is None:
                continue
            result.append("  %s" % code_info.filelineno())
            result.append("    %s" % code_info.sourceline)
        msg = "\n".join(result)
        super().__init__(msg)


class DirectiveReportError(ConfigError):
    """Raised when there's a problem with a directive.

    Describes where in the code the problem occurred.
    """

    def __init__(self, message: str, code_info: CodeInfo | None) -> None:
        result = [message]
        if code_info is not None:
            result.append("  %s" % code_info.filelineno())
            result.append("    %s" % code_info.sourceline)
        msg = "\n".join(result)
        super().__init__(msg)


class DirectiveError(ConfigError):
    """Can be raised by user when there directive cannot be performed.

    Raise it in :meth:`Action.perform` with a message describing what
    the problem is::

      raise DirectiveError("name should be a string, not None")

    This is automatically converted by Dectate to a
    :exc:`DirectiveReportError`.
    """


class TopologicalSortError(ValueError):
    """Raised if dependencies cannot be sorted topologically.

    This is due to circular dependencies.
    """


class QueryError(Exception):
    pass
