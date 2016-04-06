import dectate
from . import a, b, c


def query_tool():
    dectate.commit(a.App, a.Other)
    dectate.query_tool([a.App, a.Other])
