import sys

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:  # pragma: no cover
    text_type = str  # pragma: nocoverage
else:
    text_type = unicode

if PY3:
    string_types = (str,)  # pragma: nocoverage
else:
    string_types = (basestring,)

# Newer versions of flask and six have the following version of
# with_metaclass, which seems to have a constant number of function
# calls. Hence, stack frame navigation does not depend on the
# execution path, as previously was the case.
#
# see:
# https://github.com/pallets/flask/pull/1539
#
# and the following for a description of the problem that previous
# versions had:
#
# https://bitbucket.org/gutworth/six/issue/83/with_meta-and-stack-frame-issues
# https://github.com/PythonCharmers/python-future/issues/75
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.
    class metaclass(type):
        def __new__(cls, name, this_bases, attrs):
            return meta(name, bases, attrs)
    return type.__new__(metaclass, 'temporary_class', (), {})
