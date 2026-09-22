import pprint

import app2  # pyright: ignore[reportUnusedImport] # noqa: F401
from config import App as App

import dectate


@App.foo(name="a")
def f() -> None:
    pass


if __name__ == "__main__":
    dectate.commit(App)
    pprint.pprint(App.config.my)
