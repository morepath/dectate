import dectate
from . import a, b, c


def main():
    dectate.commit(a.App, a.Other)
    dectate.querytool([a.App, a.Other])
