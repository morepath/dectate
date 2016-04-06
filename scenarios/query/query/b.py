from .a import App, Other


@App.foo(name='alpha')
def f():
    pass


@App.foo(name='beta')
def g():
    pass


@App.foo(name='gamma')
def h():
    pass


@Other.foo(name='alpha')
def i():
    pass
