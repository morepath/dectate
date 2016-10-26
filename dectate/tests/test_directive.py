from dectate.app import App, directive
from dectate.config import commit, Action, Composite
from dectate.error import ConflictError, ConfigError

import pytest


def test_simple():
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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('hello', f)]


def test_decorator():

    class MyApp(App):
        @directive
        class foo(Action):
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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    result = MyApp.commit()

    assert MyApp.config.my == [('hello', f)]
    assert list(result) == [MyApp]


def test_directive_name():
    class MyDirective(Action):
        config = {
            'my': list
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my.append(self)

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    MyApp.commit()

    MyApp.config.my[0].directive.directive_name == 'foo'


def test_conflict_same_directive():
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

    class MyApp(App):
        foo = directive(MyDirective)

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

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

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

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

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

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

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

    class BarDirective(Action):
        # should now conflict
        group_class = FooDirective

        def __init__(self, message):
            self.message = message

        def identifier(self, foo):
            return self.message

        def perform(self, obj, foo):
            foo.append((self.message, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo('hello')
    def f():
        pass

    @MyApp.bar('hello')
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_conflict():
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

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_same_group_conflict():
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

    class BarDirective(FooDirective):
        group_class = FooDirective

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_discriminator_no_conflict():
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

    class MyApp(App):
        foo = directive(FooDirective)

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.foo('g', ['b'])
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('f', f), ('g', g)]


def test_discriminator_different_group_no_conflict():
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

    class BarDirective(FooDirective):
        # will have its own group key so in a different group
        depends = [FooDirective]

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo('f', ['a'])
    def f():
        pass

    @MyApp.bar('g', ['a', 'b'])
    def g():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('f', f), ('g', g)]


def test_depends():
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

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

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

    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    class MyApp(App):
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f), ('b', f), ('c', f)]


def test_composite_change_object():
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

    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message),
                     other) for message in self.messages]

    class MyApp(App):
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', other), ('b', other), ('c', other)]


def test_composite_private_sub():
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

    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    class MyApp(App):
        # mark sub as private by using the underscore
        _sub = directive(SubDirective)
        composite = directive(CompositeDirective)

    @MyApp.composite(['a', 'b', 'c'])
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f), ('b', f), ('c', f)]


def test_composite_private_composite():
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

    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubDirective(message), obj) for message in self.messages]

    class MyApp(App):
        sub = directive(SubDirective)
        _composite = directive(CompositeDirective)

    @MyApp.sub('a')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.my == [('a', f)]


def test_nested_composite():
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

    class SubCompositeDirective(Composite):
        def __init__(self, message):
            self.message = message

        def actions(self, obj):
            yield SubDirective(self.message + '_0'), obj
            yield SubDirective(self.message + '_1'), obj

    class CompositeDirective(Composite):
        def __init__(self, messages):
            self.messages = messages

        def actions(self, obj):
            return [(SubCompositeDirective(message), obj)
                    for message in self.messages]

    class MyApp(App):
        sub = directive(SubDirective)
        subcomposite = directive(SubCompositeDirective)
        composite = directive(CompositeDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

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

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

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

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self, my):
            return self.name

        def perform(self, obj, my):
            my.append((self.name, obj))

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

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

    class BarDirective(Action):
        group_class = FooDirective

        def __init__(self, name):
            self.name = name

        def identifier(self):
            return self.name

        def perform(self, obj):
            pass

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

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

    class MyApp(App):
        foo = directive(FooDirective)

    commit(MyApp)

    assert MyApp.config.my.after
    assert MyApp.config.my.l == []


def test_action_loop_should_conflict():
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

    class MyApp(App):
        foo = directive(MyDirective)

    for i in range(2):
        @MyApp.foo('hello')
        def f():
            pass

    with pytest.raises(ConflictError):
        commit(MyApp)


def test_action_init_only_during_commit():
    init_called = []

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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    assert init_called == []

    commit(MyApp)

    assert init_called == ["there"]


def test_registry_should_exist_even_without_directive_use():
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

    class MyApp(App):
        foo = directive(MyDirective)

    commit(MyApp)

    assert MyApp.config.my == []


def test_registry_should_exist_even_without_directive_use_subclass():
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

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

    commit(MyApp, SubApp)

    assert MyApp.config.my == []
    assert SubApp.config.my == []


def test_rerun_commit():
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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    # and again
    commit(MyApp)

    assert MyApp.config.my == [('hello', f)]


def test_rerun_commit_add_directive():
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

    class MyApp(App):
        foo = directive(MyDirective)

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

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

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
    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]


def test_registry_factory_argument_introduces_new_registry():
    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]
    assert MyApp.config.my is MyApp.config.other.my


def test_registry_factory_argument_introduces_new_registry_subclass():
    class IsUsedElsewhere(object):
        poked = False

    class Other(object):
        factory_arguments = {
            'my': IsUsedElsewhere
        }

        def __init__(self, my):
            self.my = my

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

    class MyApp(App):
        foo = directive(MyDirective)

    class SubApp(MyApp):
        pass

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my.poked
    assert MyApp.config.my is MyApp.config.other.my

    commit(SubApp)


def test_registry_multiple_factory_arguments():
    class Other(object):
        factory_arguments = {
            'my': list,
            'my2': list
        }

        def __init__(self, my, my2):
            self.my = my
            self.my2 = my2

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

    class MyApp(App):
        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]
    assert MyApp.config.other.my2 == ['blah']


def test_registry_factory_arguments_depends():
    class Other(object):
        factory_arguments = {
            'my': list
        }

        def __init__(self, my):
            self.my = my

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

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    assert MyApp.config.other.my == [('hello', f)]


def test_registry_factory_arguments_depends_complex():
    class Registry(object):
        pass

    class PredicateRegistry(object):
        factory_arguments = {
            'registry': Registry
        }

        def __init__(self, registry):
            self.registry = registry

    class SettingAction(Action):
        config = {'registry': Registry}

    class PredicateAction(Action):
        config = {'predicate_registry': PredicateRegistry}

        depends = [SettingAction]

    class ViewAction(Action):
        config = {'registry': Registry}

        depends = [PredicateAction]

    class MyApp(App):
        setting = directive(SettingAction)
        predicate = directive(PredicateAction)
        view = directive(ViewAction)

    commit(MyApp)

    assert MyApp.config.registry is MyApp.config.predicate_registry.registry


def test_is_committed():
    class MyApp(App):
        pass

    assert not MyApp.is_committed()

    commit(MyApp)

    assert MyApp.is_committed()


def test_registry_config_inconsistent():
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

    class BarDirective(Action):
        config = {
            'my': dict
        }

        def __init__(self, message):
            self.message = message

        def identifier(self, my):
            return self.message

        def perform(self, obj, my):
            my[self.message] = obj

    class MyApp(App):
        foo = directive(FooDirective)
        bar = directive(BarDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_inconsistent():
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

    class MyApp(App):
        foo = directive(MyDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


def test_registry_factory_argument_and_config_inconsistent():
    class Other(object):
        factory_arguments = {
            'my': dict
        }

        def __init__(self, my):
            self.my = my

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

    class MyApp(App):
        foo = directive(MyDirective)

    with pytest.raises(ConfigError):
        commit(MyApp)


# making this global to ensure the repr is the same
# on Python 3.5 and earlier versions (see PEP 3155)
class ReprDirective(Action):
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


class MyAppForRepr(App):
    foo = directive(ReprDirective)


def test_directive_repr():
    MyAppForRepr.commit()

    assert repr(MyAppForRepr.foo) == (
        "<bound method AppMeta.foo of "
        "<class 'dectate.tests.test_directive.MyAppForRepr'>>")


def test_app_class_passed_into_action():
    class MyDirective(Action):
        config = {
            'my': list
        }

        app_class_arg = True

        def __init__(self, message):
            self.message = message

        def identifier(self, app_class, my):
            return self.message

        def perform(self, obj, app_class, my):
            app_class.touched.append(None)
            my.append((self.message, obj))

    class MyApp(App):
        touched = []

        foo = directive(MyDirective)

    class SubApp(MyApp):
        touched = []

    @MyApp.foo('hello')
    def f():
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched == [None]

    # the subclass is not affected until we commit for it too
    assert not SubApp.touched

    commit(SubApp)

    assert SubApp.touched == [None]


def test_app_class_passed_into_factory():
    class Other(object):
        factory_arguments = {
            'my': list
        }

        app_class_arg = True

        def __init__(self, my, app_class):
            self.my = my
            self.app_class = app_class

        def touch(self):
            self.app_class.touched = True

    class MyDirective(Action):
        config = {
            'other': Other
        }

        def __init__(self):
            pass

        def identifier(self, other):
            return ()

        def perform(self, obj, other):
            other.touch()

    class MyApp(App):
        touched = False

        foo = directive(MyDirective)

    @MyApp.foo()
    def f():
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched


def test_app_class_passed_into_factory_no_factory_arguments():
    class Other(object):
        app_class_arg = True

        def __init__(self, app_class):
            self.app_class = app_class

        def touch(self):
            self.app_class.touched = True

    class MyDirective(Action):
        config = {
            'other': Other
        }

        def __init__(self):
            pass

        def identifier(self, other):
            return ()

        def perform(self, obj, other):
            other.touch()

    class MyApp(App):
        touched = False

        foo = directive(MyDirective)

    @MyApp.foo()
    def f():
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched


def test_app_class_passed_into_factory_separation():
    class Other(object):
        factory_arguments = {
            'my': list
        }

        app_class_arg = True

        def __init__(self, my, app_class):
            self.my = my
            self.app_class = app_class

        def touch(self):
            self.app_class.touched = True

    class MyDirective(Action):
        config = {
            'other': Other
        }

        def __init__(self):
            pass

        def identifier(self, other):
            return ()

        def perform(self, obj, other):
            other.touch()

    class MyApp(App):
        touched = False
        foo = directive(MyDirective)

    class SubApp(MyApp):
        touched = False

    @MyApp.foo()
    def f():
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched

    assert not SubApp.touched

    commit(SubApp)

    assert SubApp.touched


def test_app_class_cleanup():
    class MyDirective(Action):
        config = {
        }

        app_class_arg = True

        def __init__(self):
            pass

        def identifier(self, app_class):
            return ()

        def perform(self, obj, app_class):
            app_class.touched.append(None)

    class MyApp(App):
        touched = []

        @classmethod
        def clean(cls):
            cls.touched = []

        foo = directive(MyDirective)

    @MyApp.foo()
    def f():
        pass

    assert not MyApp.touched

    commit(MyApp)

    assert MyApp.touched == [None]

    commit(MyApp)

    assert MyApp.touched == [None]
