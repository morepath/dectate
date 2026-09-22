from .a import App, Other


@App.foo(name="alpha")
def f() -> None:
    pass


@App.foo(name="beta")
def g() -> None:
    pass


@App.foo(name="gamma")
def h() -> None:
    pass


@Other.foo(name="alpha")
def i() -> None:
    pass
