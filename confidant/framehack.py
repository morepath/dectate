import sys
import inspect
import os


class FrameInfo(object):
    """FrameInfo object.
    """
    def __init__(self, kind, module, path, lineno, sourceline):
        self.kind = kind
        self.module = module
        self.path = path
        self.lineno = lineno
        self.sourceline = sourceline


# taken from pyramid.path
def caller_module(level=2, sys=sys):
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def caller_package(level=2, caller_module=caller_module):
    # caller_module in arglist for tests
    module = caller_module(level + 1)
    f = getattr(module, '__file__', '')
    if ('__init__.py' in f) or ('__init__$py' in f):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]


def get_frame_info(frame):
    """Return a FrameInfo object describing the frame.

    `frameinfo.kind` is one of "exec", "module", "class", "function
    call", or "unknown".

    Adapted from getFrameInfo in Venusian's 'advice', which originally comes
    from PEAK. http://peak.telecommunity.co
    """
    f_locals = frame.f_locals
    f_globals = frame.f_globals

    same_namespace = f_locals is f_globals
    has_module = '__module__' in f_locals
    has_name = '__name__' in f_globals

    same_name = has_module and has_name
    same_name = same_name and f_globals['__name__'] == f_locals['__module__']

    module = has_name and sys.modules.get(f_globals['__name__']) or None

    namespace_is_module = module and module.__dict__ is f_globals

    if not namespace_is_module:  # pragma no COVER
        # some kind of funky exec
        kind = "exec"  # don't know how to repeat this scenario
    elif same_namespace and not has_module:
        kind = "module"
    elif same_name and not same_namespace:
        kind = "class"
    elif not same_namespace:
        kind = "function call"
    else:  # pragma NO COVER
        # How can you have f_locals is f_globals, and have '__module__' set?
        # This is probably module-level code, but with a '__module__' variable.
        kind = "unknown"

    frameinfo = inspect.getframeinfo(frame)

    try:
        sourceline = frameinfo.code_context[0].strip()
    except:  # pragma NO COVER
        # dont understand circumstance here, 3rdparty code without comment
        sourceline = frameinfo.code_context

    # if we are in __main__, make path absolute
    if f_globals['__name__'] == '__main__':
        path = os.path.join(os.getcwd(), frameinfo.filename)
    else:
        path = frameinfo.filename

    return FrameInfo(
        kind=kind,
        module=module,
        path=path,
        lineno=frameinfo.lineno,
        sourceline=sourceline)
