from dectate.app import App
from dectate.config import commit, Action, Composite
from dectate.error import ConflictError, ConfigError

import pytest


def test_simple():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('hello', f)]


def test_commit_method():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    result = MyApp.commit()

    assert MyApp.config.my == [('hello', f)]
    assert list(result) == [MyApp]


def test_conflict_same_directive():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.foo('hello')
    def f2():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_app_inherit():
    class Registry(object):
        pass

    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
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

    commit(MyApp, SubApp)

    assert MyApp.config.my.message == 'hello'
    assert MyApp.config.my.obj is f
    assert SubApp.config.my.message == 'hello'
    assert SubApp.config.my.obj is f


def test_app_override():
    class Registry(object):
        pass

    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
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

    commit(MyApp, SubApp)

    assert MyApp.config.my.message == 'hello'
    assert MyApp.config.my.obj is f
    assert SubApp.config.my.message == 'hello'
    assert SubApp.config.my.obj is f2


def test_different_group_no_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        config = {
            'bar': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, bar):
            return self.message

        def perform(self, obj, bar):
            bar.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.foo == [('hello', f)]
    assert MyApp.config.bar == [('hello', g)]


def test_same_group_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'foo': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        # should now conflict
        group_class = FooDirective

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_same_group_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        group_class = FooDirective

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_no_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['b'])
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('f', f), ('g', g)]


def test_discriminator_different_group_no_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message, others):
            self.message = message
            self.others = others

        def identifier(self, my):
            return self.message

        def discriminators(self, my):
            return self.others

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(FooDirective):
        # will have its own group key so in a different group
        depends = [FooDirective]

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('f', f), ('g', g)]


def test_depends():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        depends = [FooDirective]

        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.bar('a')
    def g():
        pass

    @MyApp.foo('b')
    def f():
        pass

    commit(MyApp)

    # since bar depends on foo, it should be executed last
    assert MyApp.config.my == [('b', f), ('a', g)]


def test_composite():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f), ('b', f), ('c', f)]


def test_composite_change_object():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    def other():
        pass

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message),
                     other) for message in self.messages]

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', other), ('b', other), ('c', other)]


def test_composite_private_sub():
    class MyApp(App):
        pass

    @MyApp.private_action_class
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('composite')
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f), ('b', f), ('c', f)]


def test_composite_private_composite():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.private_action_class
    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    @MyApp.sub('a')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f)]


def test_nested_composite():
    class MyApp(App):
        pass

    @MyApp.directive('sub')
    class SubDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

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

    commit(MyApp)

    # since bar depends on foo, it should be executed last
    assert MyApp.config.my == [
        ('a_0', f), ('a_1', f),
        ('b_0', f), ('b_1', f),
        ('c_0', f), ('c_1', f)]


def test_with_statement_kw():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, my):
            return (self.model, self.name)

        def perform(self, obj, my):
            my.append((self.model, self.name, obj))

    class Dummy(object):
        pass

    with MyApp.foo(model=Dummy) as foo:

        @foo(name='a')
        def f():
            pass

        @foo(name='b')
        def g():
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, 'a', f),
        (Dummy, 'b', g),
    ]


def test_with_statement_args():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, model, name):
            self.model = model
            self.name = name

        def identifier(self, my):
            return (self.model, self.name)

        def perform(self, obj, my):
            my.append((self.model, self.name, obj))

    class Dummy(object):
        pass

    with MyApp.foo(Dummy) as foo:

        @foo('a')
        def f():
            pass

        @foo('b')
        def g():
            pass

    commit(MyApp)

    assert MyApp.config.my == [
        (Dummy, 'a', f),
        (Dummy, 'b', g),
    ]


def test_before():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.before = False

        def add(self, name, obj):
            assert self.before
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def before(my):
            my.before = True

    @MyApp.foo(name='hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.l == [
        ('hello', f),
    ]


def test_before_without_use():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.before = False

        def add(self, name, obj):
            assert self.before
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def before(my):
            my.before = True

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.l == []


def test_before_group():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.before = False

        def add(self, name, obj):
            assert self.before
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def before(my):
            my.before = True

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            pass

    @MyApp.bar(name='bye')
    def f():
        pass

    @MyApp.foo(name='hello')
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.l == [
        ('hello', g),
    ]


def test_config_group():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.append((self.name, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.append((self.name, obj))

    @MyApp.bar(name='bye')
    def f():
        pass

    @MyApp.foo(name='hello')
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my == [
        ('bye', f), ('hello', g),
    ]


def test_before_group_without_use():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.before = False

        def add(self, name, obj):
            assert self.before
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def before(my):
            my.before = True

    @MyApp.directive('bar')
    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            pass

    commit(MyApp)

    assert MyApp.config.my.before
    assert MyApp.config.my.l == []


def test_after():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.after = False

        def add(self, name, obj):
            assert not self.after
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def after(my):
            my.after = True

    @MyApp.foo(name='hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my.after
    assert MyApp.config.my.l == [
        ('hello', f),
    ]


def test_after_without_use():
    class Registry(object):
        def __init__(self):
            self.l = []
            self.after = False

        def add(self, name, obj):
            assert not self.after
            self.l.append((name, obj))

    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': Registry
        }

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.add(self.name, obj)

        @staticmethod
        def after(my):
            my.after = True

    commit(MyApp)

    assert MyApp.config.my.after
    assert MyApp.config.my.l == []


def test_action_loop_should_conflict():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    for i in range(2):
        @MyApp.foo('hello')
        def f():
            pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_action_init_only_during_commit():
    class MyApp(App):
        pass

    init_called = []

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            init_called.append("there")
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    assert init_called == []

    commit(MyApp)

    assert init_called == ["there"]


def test_registry_should_exist_even_without_directive_use():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    commit(MyApp)

    assert MyApp.config.my == []


def test_registry_should_exist_even_without_directive_use_subclass():
    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    commit(MyApp, SubApp)

    assert MyApp.config.my == []
    assert SubApp.config.my == []


def test_rerun_commit():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    # and again
    commit(MyApp)

    assert MyApp.config.my == [('hello', f)]


def test_rerun_commit_add_directive():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    @MyApp.foo('bye')
    def g():
        pass

    # and again
    commit(MyApp)

    assert MyApp.config.my == [('hello', f), ('bye', g)]


def test_order_subclass():
    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @SubApp.foo('c')
    def h():
        pass

    @MyApp.foo('a')
    def f():
        pass

    @MyApp.foo('b')
    def g():
        pass

    commit(MyApp, SubApp)

    assert SubApp.config.my == [('a', f), ('b', g), ('c', h)]


def test_registry_single_factory_argument():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list,
            'other': Other
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my, other):
            return self.message

        def perform(self, obj, my, other):
            my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]


def test_registry_factory_argument_introduces_new_registry():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'other': Other
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, other):
            return self.message

        def perform(self, obj, other):
            other.my.append((self.message, obj))

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]
    assert MyApp.config.my is MyApp.config.other.my


def test_registry_factory_argument_introduces_new_registry_subclass():
    class MyApp(App):
        pass

    class SubApp(MyApp):
        pass

    class IsUsedElsewhere(object):
        poked = False

    class Other(object):
        factory_arguments = {
            'my': IsUsedElsewhere
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'other': Other
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, other):
            return self.message

        def perform(self, obj, other):
            assert not other.my.poked
            other.my.poked = True

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my.poked
    assert MyApp.config.my is MyApp.config.other.my

    commit(SubApp)


def test_registry_multiple_factory_arguments():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': list,
            'my2': list
        }

        def __init__(self, my, my2):
            self.my = my
            self.my2 = my2

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list,
            'my2': list,
            'other': Other
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my, my2, other):
            return self.message

        def perform(self, obj, my, my2, other):
            my.append((self.message, obj))
            my2.append('blah')

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]
    assert MyApp.config.other.my2 == ['blah']


def test_registry_factory_arguments_depends():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class FooDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('bar')
    class BarDirective(Action):
        config = {
            'other': Other
        }

        depends = [FooDirective]

        def __init__(self, name):
            self.name = name

        def identifier(self, other):
            return self.name

        def perform(self, obj, other):
            pass

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]


def test_registry_factory_arguments_depends_complex():
    class MyApp(App):
        pass

    class Registry(object):
        pass

    class PredicateRegistry(object):
        factory_arguments = {
            'registry': Registry
        }

        def __init__(self, registry):
            self.registry = registry

    @MyApp.directive('setting')
    class SettingAction(Action):
        config = {'registry': Registry}

    @MyApp.directive('predicate')
    class PredicateAction(Action):
        config = {'predicate_registry': PredicateRegistry}

        depends = [SettingAction]

    @MyApp.directive('view')
    class ViewAction(Action):
        config = {'registry': Registry}

        depends = [PredicateAction]

    commit(MyApp)

    assert MyApp.config.registry is MyApp.config.predicate_registry.registry


def test_is_committed():
    class MyApp(App):
        pass

    assert not MyApp.is_committed()

    commit(MyApp)

    assert MyApp.is_committed()


def test_registry_config_inconsistent():
    class MyApp(App):
        pass

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    @MyApp.directive('bar')
    class MyDirective(Action):  # flake8: noqa
        config = {
            'my': dict
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my[self.message] = obj

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_inconsistent():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

    class YetAnother(object):
        factory_arguments = {
            'my': dict
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'other': Other,
            'yetanother': YetAnother
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, other, yetanother):
            return self.message

        def perform(self, obj, other, yetanother):
            pass

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_and_config_inconsistent():
    class MyApp(App):
        pass

    class Other(object):
        factory_arguments = {
            'my': dict
        }

        def __init__(self, my):
            self.my = my

    @MyApp.directive('foo')
    class MyDirective(Action):
        config = {
            'my': list,
            'other': Other
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my, other):
            return self.message

        def perform(self, obj, my, other):
            my.append((self.message, obj))

    with pytest.raises(ConfigError):
        commit(MyApp)


# Due to PEP 3155, having this class defined at the module top-level ensures
# that its repr is the same in both Python 2 and 3.
class MyAppForRepr(App):
    pass


def test_directive_repr():

    @MyAppForRepr.directive('foo')
    class MyDirective(Action):
        """Doc"""
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append((self.message, obj))

    assert repr(MyAppForRepr.foo) == (
        "<bound method AppMeta.foo of "
        "<class 'dectate.tests.test_directive.MyAppForRepr'>>")
