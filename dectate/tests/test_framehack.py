import sys
from dectate.framehack import get_frame_info


def foo():
    frame = sys._getframe(1)
    info = get_frame_info(frame)
    return info


def test_framehack_function_call():
    info = foo()
    assert info.kind == 'function call'
    assert info.module == sys.modules[__name__]
    assert info.path == __file__
    assert info.lineno == 12
    assert info.sourceline == 'info = foo()'


toplevel = foo()


def test_framehack_toplevel():
    assert toplevel.kind == 'module'
    assert toplevel.module == sys.modules[__name__]
    assert toplevel.path == __file__
    assert toplevel.lineno == 20
    assert toplevel.sourceline == 'toplevel = foo()'


class Foo(object):
    info = foo()


def test_framehack_class():
    assert Foo.info.kind == 'class'
