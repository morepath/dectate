from dectate.app import App
from dectate.config import Config, Action, Composite
from dectate.error import ConflictError

import pytest


def test_simple():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    assert MyApp.configurations.my.l == [('hello', f)]


def test_conflict_same_directive():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.foo('hello')
    def f2():
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_app_inherit():
    config = Config()

    class Registry(object):
        pass

    class MyApp(App):
        testing_config = config

    class SubApp(MyApp):
        testing_config = config

    @MyApp.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.message = self.message
            my.obj = obj

    @MyApp.foo('hello')
    def f():
        pass

    config.commit()

    assert MyApp.configurations.my.message == 'hello'
    assert MyApp.configurations.my.obj is f
    assert SubApp.configurations.my.message == 'hello'
    assert SubApp.configurations.my.obj is f


def test_app_override():
    config = Config()

    class Registry(object):
        pass

    class MyApp(App):
        testing_config = config

    class SubApp(MyApp):
        testing_config = config

    @MyApp.directive('foo')
    class MyDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.message = self.message
            my.obj = obj

    @MyApp.foo('hello')
    def f():
        pass

    @SubApp.foo('hello')
    def f2():
        pass

    config.commit()

    assert MyApp.configurations.my.message == 'hello'
    assert MyApp.configurations.my.obj is f
    assert SubApp.configurations.my.message == 'hello'
    assert SubApp.configurations.my.obj is f2


def test_different_group_no_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'foo': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.add(self.message, obj)

    @MyApp.directive('bar')
    class BarDirective(Action):
        configurations = {
            'bar': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, bar):
            return self.message

        def perform(self, obj, bar):
            bar.add(self.message, obj)

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    config.commit()

    assert MyApp.configurations.foo.l == [('hello', f)]
    assert MyApp.configurations.bar.l == [('hello', g)]


def test_same_group_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'foo': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.add(self.message, obj)

    @MyApp.directive('bar')
    class BarDirective(Action):
        configurations = {
            'bar': Registry
        }

        def __init__(self, message):
            self.message = message

        # should now conflict
        def group_key(self):
            return FooDirective

        def identifier(self, bar):
            return self.message

        def perform(self, obj, bar):
            bar.add(self.message, obj)

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_discriminator_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    @App.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.add(self.message, obj)

    class MyApp(App):
        testing_config = config

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_discriminator_same_group_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        def group_key(self):
            return FooDirective

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        config.commit()


def test_discriminator_no_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['b'])
    def g():
        pass

    config.commit()


def test_discriminator_different_group_no_conflict():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        # will have its own group key so in a different group
        pass

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    config.commit()


def test_depends():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.directive('bar')
    class BarDirective(Action):
        depends = [FooDirective]

        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.bar('a')
    def g():
        pass

    @MyApp.foo('b')
    def f():
        pass

    config.commit()

    # since bar depends on foo, it should be executed last
    assert MyApp.configurations.my.l == [('b', f), ('a', g)]


def test_composite():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('sub')
    class SubDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    config.commit()

    # since bar depends on foo, it should be executed last
    assert MyApp.configurations.my.l == [('a', f), ('b', f), ('c', f)]


def test_nested_composite():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, message, obj):
            self.l.append((message, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('sub')
    class SubDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.add(self.message, obj)

    @MyApp.directive('subcomposite')
    class SubCompositeDirective(Composite):
        def __init__(self, message):
            self.message = message

        def actions(self, obj):
            yield SubDirective(self.message + '_0'), obj
            yield SubDirective(self.message + '_1'), obj

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubCompositeDirective(message), obj)
                    for message in self.messages]

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    config.commit()

    # since bar depends on foo, it should be executed last
    assert MyApp.configurations.my.l == [
        ('a_0', f), ('a_1', f),
        ('b_0', f), ('b_1', f),
        ('c_0', f), ('c_1', f)]


def test_with_statement_kw():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, model, name, obj):
            self.l.append((model, name, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, my):
            return (self.model, self.name)

        def perform(self, obj, my):
            my.add(self.model, self.name, obj)

    class Dummy(object):
        pass

    with MyApp.foo(model=Dummy) as foo:

        @foo(name='a')
        def f():
            pass

        @foo(name='b')
        def g():
            pass

    config.commit()

    assert MyApp.configurations.my.l == [
        (Dummy, 'a', f),
        (Dummy, 'b', g),
    ]


def test_with_statement_args():
    config = Config()

    class Registry(object):
        def __init__(self):
            self.l = []

        def add(self, model, name, obj):
            self.l.append((model, name, obj))

    class MyApp(App):
        testing_config = config

    @MyApp.directive('foo')
    class FooDirective(Action):
        configurations = {
            'my': Registry
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, my):
            return (self.model, self.name)

        def perform(self, obj, my):
            my.add(self.model, self.name, obj)

    class Dummy(object):
        pass

    with MyApp.foo(Dummy) as foo:

        @foo('a')
        def f():
            pass

        @foo('b')
        def g():
            pass

    config.commit()

    assert MyApp.configurations.my.l == [
        (Dummy, 'a', f),
        (Dummy, 'b', g),
    ]
