# -*- coding: utf-8 -*-


class ConfigError(Exception):
    """Raised when configuration is bad
    """


def conflict_keyfunc(action):
    code_info = action.code_info()
    if code_info is None:
        return 0
    return (code_info.path, code_info.lineno)


class ConflictError(ConfigError):
    """Raised when there is a conflict in configuration.
    """
    def __init__(self, actions):
        actions.sort(key=conflict_keyfunc)
        self.actions = actions
        result = [
            'Conflict between:']
        for action in actions:
            code_info = action.code_info()
            if code_info is None:
                continue
            result.append('  File "%s", line %s' % (code_info.path,
                                                    code_info.lineno))
            result.append('    %s' % code_info.sourceline)
        msg = '\n'.join(result)
        super(ConflictError, self).__init__(msg)


class DirectiveReportError(ConfigError):
    """Raised when there's a problem with a directive.
    """
    def __init__(self, message, action):
        code_info = action.code_info()
        result = [message]
        if code_info is not None:
            result.append('  File "%s", line %s' % (code_info.path,
                                                    code_info.lineno))
            result.append('    %s' % code_info.sourceline)
        msg = '\n'.join(result)
        super(DirectiveReportError, self).__init__(msg)


class DirectiveError(ConfigError):
    pass


class TopologicalSortError(Exception):
    pass
