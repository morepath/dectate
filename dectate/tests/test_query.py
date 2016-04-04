from dectate import Query, execute, App, Action, commit


def test_query():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
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

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).attrs('name')

    assert list(execute(MyApp, q)) == [
        {'name': 'a'},
        {'name': 'b'}
    ]


def test_filter():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
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

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='a').attrs('name')

    assert list(execute(MyApp, q)) == [
        {'name': 'a'},
    ]



def test_filter_multiple_fields():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, registry):
            return (self.model, self.name)

        def perform(self, obj, registry):
            registry.append((self.model, self.name, obj))

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

    assert list(execute(MyApp, q.filter(model=Alpha, name='a').obj())) == [f]
    assert list(execute(MyApp, q.filter(model=Alpha, name='b').obj())) == [g]
    assert list(execute(MyApp, q.filter(model=Beta, name='a').obj())) == [h]
    assert list(execute(MyApp, q.filter(model=Beta, name='b').obj())) == [i]


def test_filter_not_found():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
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

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(unknown='a').attrs('name')

    assert list(execute(MyApp, q)) == []


def test_filter_different_attribute_name():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooAction(Action):
        config = {
            'registry': list
        }

        query_names = {
            'name': '_name'
        }

        def __init__(self, name):
            self._name = name

        def identifier(self, registry):
            return self._name

        def perform(self, obj, registry):
            registry.append((self._name, obj))

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp)

    q = Query(FooAction).filter(name='a').attrs('name')

    assert list(execute(MyApp, q)) == [{'name': 'a'}]


def test_filter_class():
    class MyApp(App):
        pass

    @MyApp.directive('view')
    class ViewAction(Action):
        config = {
            'registry': list
        }

        def __init__(self, model):
            self.model = model

        def identifier(self, registry):
            return self.model

        def perform(self, obj, registry):
            registry.append((self.model, obj))

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

    assert list(execute(
        MyApp,
        Query(ViewAction).filter(model=Alpha).obj())) == [f]

    assert list(execute(
        MyApp,
        Query(ViewAction).filter(model=Beta).obj())) == [g, h, i]

    assert list(execute(
        MyApp,
        Query(ViewAction).filter(model=Gamma).obj())) == [h, i]

    assert list(execute(
        MyApp,
        Query(ViewAction).filter(model=Delta).obj())) == [i]
