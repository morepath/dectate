import pytest

from dectate import (
    Query, App, Action, Composite, directive, commit, QueryError, NOT_FOUND)


def test_query():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_query_directive_name():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query('foo').attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_multi_action_query():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class BarAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)
        bar = directive(BarAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.bar('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction, BarAction).attrs('name')

    assert sorted(list(q(MyApp)), key=lambda d: d['name']) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_filter():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='a').attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
    ]


def test_filter_multiple_fields():
    class FooAction(Action):
        config = {
            'registry': list
        }

        filter_compare = {
            'model': issubclass
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, registry):
            return (self.model, self.name)

        def perform(self, obj, registry):
            registry.append((self.model, self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    class Alpha(object):
        pass

    class Beta(object):
        pass

    @MyApp.foo(model=Alpha, name='a')
    def f():
        pass

    @MyApp.foo(model=Alpha, name='b')
    def g():
        pass

    @MyApp.foo(model=Beta, name='a')
    def h():
        pass

    @MyApp.foo(model=Beta, name='b')
    def i():
        pass

    commit(MyApp)

    q = Query(FooAction)

    assert list(q.filter(model=Alpha, name='a').obj()(MyApp)) == [f]
    assert list(q.filter(model=Alpha, name='b').obj()(MyApp)) == [g]
    assert list(q.filter(model=Beta, name='a').obj()(MyApp)) == [h]
    assert list(q.filter(model=Beta, name='b').obj()(MyApp)) == [i]


def test_filter_not_found():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(unknown='a').attrs('name')

    assert list(q(MyApp)) == []


def test_filter_different_attribute_name():
    class FooAction(Action):
        config = {
            'registry': list
        }

        filter_name = {
            'name': '_name'
        }

        def __init__(self, name):
            self._name = name

        def identifier(self, registry):
            return self._name

        def perform(self, obj, registry):
            registry.append((self._name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='a').attrs('name')

    assert list(q(MyApp)) == [{'name': 'a'}]


def test_filter_get_value():
    class FooAction(Action):
        def filter_get_value(self, name):
            return self.kw.get(name, NOT_FOUND)

        def __init__(self, **kw):
            self.kw = kw

        def identifier(self):
            return tuple(sorted(self.kw.items()))

        def perform(self, obj):
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo(x='a', y='b')
    def f():
        pass

    @MyApp.foo(x='a', y='c')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(x='a').attrs('x', 'y')

    assert list(q(MyApp)) == [{'x': 'a', 'y': 'b'},
                              {'x': 'a', 'y': 'c'}]

    q = Query(FooAction).filter(y='b').attrs('x', 'y')

    assert list(q(MyApp)) == [{'x': 'a', 'y': 'b'}]


def test_filter_name_and_get_value():
    class FooAction(Action):
        filter_name = {
            'name': '_name'
        }

        def filter_get_value(self, name):
            return self.kw.get(name, NOT_FOUND)

        def __init__(self, name, **kw):
            self._name = name
            self.kw = kw

        def identifier(self):
            return tuple(sorted(self.kw.items()))

        def perform(self, obj):
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo(name='hello', x='a', y='b')
    def f():
        pass

    @MyApp.foo(name='bye', x='a', y='c')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='hello').attrs('name', 'x', 'y')

    assert list(q(MyApp)) == [{'x': 'a', 'y': 'b', 'name': 'hello'}]


def test_filter_get_value_and_default():
    class FooAction(Action):
        def filter_get_value(self, name):
            return self.kw.get(name, NOT_FOUND)

        def __init__(self, name, **kw):
            self.name = name
            self.kw = kw

        def identifier(self):
            return tuple(sorted(self.kw.items()))

        def perform(self, obj):
            pass

    class MyApp(App):
        foo = directive(FooAction)

    @MyApp.foo(name='hello', x='a', y='b')
    def f():
        pass

    @MyApp.foo(name='bye', x='a', y='c')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='hello').attrs('name', 'x', 'y')

    assert list(q(MyApp)) == [{'x': 'a', 'y': 'b', 'name': 'hello'}]


def test_filter_class():
    class ViewAction(Action):
        config = {
            'registry': list
        }

        filter_compare = {
            'model': issubclass
        }

        def __init__(self, model):
            self.model = model

        def identifier(self, registry):
            return self.model

        def perform(self, obj, registry):
            registry.append((self.model, obj))

    class MyApp(App):
        view = directive(ViewAction)

    class Alpha(object):
        pass

    class Beta(object):
        pass

    class Gamma(Beta):
        pass

    class Delta(Gamma):
        pass

    @MyApp.view(model=Alpha)
    def f():
        pass

    @MyApp.view(model=Beta)
    def g():
        pass

    @MyApp.view(model=Gamma)
    def h():
        pass

    @MyApp.view(model=Delta)
    def i():
        pass

    commit(MyApp)

    assert list(Query(ViewAction).filter(model=Alpha).obj()(MyApp)) == [f]

    assert list(Query(ViewAction).filter(model=Beta).obj()(MyApp)) == [g, h, i]

    assert list(Query(ViewAction).filter(model=Gamma).obj()(MyApp)) == [h, i]

    assert list(Query(ViewAction).filter(model=Delta).obj()(MyApp)) == [i]


def test_query_group_class():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class BarAction(FooAction):
        group_class = FooAction

    class MyApp(App):
        foo = directive(FooAction)
        bar = directive(BarAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.bar('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_query_on_group_class_action():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class BarAction(FooAction):
        group_class = FooAction

    class MyApp(App):
        foo = directive(FooAction)
        bar = directive(BarAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.bar('b')
    def g():
        pass

    commit(MyApp)

    q = Query(BarAction).attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_multi_query_on_group_class_action():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class BarAction(FooAction):
        group_class = FooAction

    class MyApp(App):
        foo = directive(FooAction)
        bar = directive(BarAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.bar('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction, BarAction).attrs('name')

    assert sorted(list(q(MyApp)), key=lambda d: d['name']) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_inheritance():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    class SubApp(MyApp):
        pass

    @MyApp.foo('a')
    def f():
        pass

    @SubApp.foo('b')
    def g():
        pass

    commit(SubApp)

    q = Query(FooAction).attrs('name')

    assert list(q(SubApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_composite_action():
    class SubAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class CompositeAction(Composite):
        query_classes = [
            SubAction
        ]

        def __init__(self, names):
            self.names = names

        def actions(self, obj):
            return [(SubAction(name), obj) for name in self.names]

    class MyApp(App):
        _sub = directive(SubAction)
        composite = directive(CompositeAction)

    @MyApp.composite(['a', 'b'])
    def f():
        pass

    commit(MyApp)

    q = Query(CompositeAction).attrs('name')

    assert list(q(MyApp)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_composite_action_without_query_classes():
    class SubAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class CompositeAction(Composite):
        def __init__(self, names):
            self.names = names

        def actions(self, obj):
            return [(SubAction(name), obj) for name in self.names]

    class MyApp(App):
        _sub = directive(SubAction)
        composite = directive(CompositeAction)

    @MyApp.composite(['a', 'b'])
    def f():
        pass

    commit(MyApp)

    q = Query(CompositeAction).attrs('name')

    with pytest.raises(QueryError):
        list(q(MyApp))


def test_nested_composite_action():
    class SubSubAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class SubAction(Composite):
        query_classes = [
            SubSubAction
        ]

        def __init__(self, names):
            self.names = names

        def actions(self, obj):
            return [(SubSubAction(name), obj) for name in self.names]

    class CompositeAction(Composite):
        query_classes = [
            SubAction
        ]

        def __init__(self, amount):
            self.amount = amount

        def actions(self, obj):
            for i in range(self.amount):
                yield SubAction(['a%s' % i, 'b%s' % i]), obj

    class MyApp(App):
        _subsub = directive(SubSubAction)
        _sub = directive(SubAction)
        composite = directive(CompositeAction)

    @MyApp.composite(2)
    def f():
        pass

    commit(MyApp)

    q = Query(CompositeAction).attrs('name')

    assert sorted(list(q(MyApp)), key=lambda d: d['name']) == [
        {'name': 'a0'},
        {'name': 'a1'},
        {'name': 'b0'},
        {'name': 'b1'},
    ]


def test_query_action_for_other_app():
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class BarAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, registry):
            return self.name

        def perform(self, obj, registry):
            registry.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooAction)

    class OtherApp(App):
        bar = directive(BarAction)

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(BarAction)

    with pytest.raises(QueryError):
        list(q(MyApp))
