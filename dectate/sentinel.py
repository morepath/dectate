class Sentinel(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<%s>" % self.name


NOT_FOUND = Sentinel("NOT_FOUND")
"""Sentinel value returned if filter value cannot be found on action."""
