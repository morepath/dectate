# -*- coding: utf-8 -*-


class ConfigError(Exception):
    """Raised when configuration is bad
    """


def conflict_keyfunc(action):
    frame_info = action.frame_info()
    if frame_info is None:
        return 0
    return (frame_info.path, frame_info.lineno)


class ConflictError(ConfigError):
    """Raised when there is a conflict in configuration.
    """
    def __init__(self, actions):
        actions.sort(key=conflict_keyfunc)
        self.actions = actions
        result = [
            'Conflict between:']
        for action in actions:
            frame_info = action.frame_info()
            if frame_info is None:
                continue
            result.append('  File "%s", line %s' % (frame_info.path,
                                                    frame_info.lineno))
            result.append('    %s' % frame_info.sourceline)
        msg = '\n'.join(result)
        super(ConflictError, self).__init__(msg)


class DirectiveReportError(ConfigError):
    """Raised when there's a problem with a directive.
    """
    def __init__(self, message, action):
        frame_info = action.frame_info()
        result = [message]
        if frame_info is not None:
            result.append('  File "%s", line %s' % (frame_info.path,
                                                    frame_info.lineno))
            result.append('    %s' % frame_info.sourceline)
        msg = '\n'.join(result)
        super(DirectiveReportError, self).__init__(msg)


class DirectiveError(ConfigError):
    pass


class TopologicalSortError(Exception):
    pass
