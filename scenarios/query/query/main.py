import dectate

from . import a, b, c  # pyright: ignore[reportUnusedImport] # noqa: F401


def query_tool() -> None:
    dectate.commit(a.App, a.Other)
    dectate.query_tool([a.App, a.Other])
