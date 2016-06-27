Using Dectate
=============

Introduction
------------

Dectate is a configuration system that can help you construct Python
frameworks. A framework needs to record some information about the
functions and classes that the user supplies. We call this process
*configuration*.

Imagine for instance a framework that supports a certain kind of
plugins. The user registers each plugin with a decorator::

   from framework import plugin

   @plugin(name="foo")
   def foo_plugin(...):
      ...

Here the framework registers as a plugin the function ``foo_plugin``
under the name ``foo``.

You can implement the ``plugin`` decorator as follows::

   plugins = {}

   class plugin(name):
       def __init__(self, name):
           self.name = name

       def __call__(self, f):
          plugins[self.name] = f

In the user application the user makes sure to import all modules that
use the ``plugin`` decorator. As a result, the ``plugins`` dict
contains the names as keys and the functions as values. Your framework
can then use this information to do whatever you need to do.

There are a lot of examples of code configuration in frameworks. In a
web framework for instance the user can declare routes and assemble
middleware.

You may be okay constructing a framework with the simple decorator
technique described above. But advanced frameworks need a lot more
that the basic decorator system described above cannot offer. You may
for instance want to allow the user to reuse configuration, override
it, do more advanced error checking, and execute configuration in a
particular order.

Dectate supports such advanced use cases. It was extracted from the
Morepath_ web framework.

.. _Morepath: http://morepath.readthedocs.io

Features
--------

Here are some features of Dectate:

* Decorator-based configuration -- users declare things by using
  Python decorators on functions and classes: we call these decorators
  *directives*, which issue configuration *actions*.

* Dectate detects conflicts between configuration actions in user code
  and reports what pieces of code are in conflict.

* Users can easily reuse and extend configuration: it's just Python
  class inheritance.

* Users can easily override configurations in subclasses.

* You can compose configuration actions from other, simpler ones.

* You can control the order in which configuration actions are
  executed. This is unrelated to where the user uses the directives in
  code. You do this by declaring *dependencies* between types of
  configuration actions, and by *grouping* configuration actions
  together.

* You can declare exactly what objects are used by a type of
  configuration action to register the configuration -- different
  types of actions can use different registries.

* Unlike normal decorators, configuration actions aren't performed
  immediately when a module is imported. Instead configuration actions
  are executed only when the user explicitly *commits* the
  configuration. This way, all configuration actions are known when
  they are performed.

* Dectate-based decorators always return the function or class object
  that is decorated unchanged, which makes the code more predictable
  for a Python programmer -- the user can use the decorated function
  or class directly in their Python code, just like any other.

* Dectate-based configuration systems are themselves easily extensible
  with new directives and registries.

* Dectate-based configuration systems can be queried. Dectate also
  provides the infrastructure to easily construct command-line tools
  for querying configuration.

App classes
-----------

Configuration in Dectate is associated with special *classes* which
derive from :class:`dectate.App`:

.. testcode::

  import dectate

  class MyApp(dectate.App):
      pass

Creating a directive
--------------------

We can now use the :meth:`dectate.App.directive` decorator to declare
a *directive* which executes a special configuration action. Let's
replicate the simple `plugins` example above using Dectate:

.. testcode::

  @MyApp.directive('plugin')
  class PluginAction(dectate.Action):
      config = {
         'plugins': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, plugins):
          return self.name

      def perform(self, obj, plugins):
          plugins[self.name] = obj

Let's use it now:

.. testcode::

  @MyApp.plugin('a')
  def f():
      pass # do something interesting

  @MyApp.plugin('b')
  def g():
      pass # something else interesting

We have registered the function ``f`` on ``MyApp``. The ``name``
argument is ``'a'``. We've registered ``g`` under ``'b'``.

We can now commit the configuration for ``MyApp``:

.. testcode::

  dectate.commit(MyApp)

Once the commit has successfully completed, we can take a look at the
configuration:

.. doctest::

  >>> sorted(MyApp.config.plugins.items())
  [('a', <function f at ...>), ('b', <function g at ...>)]

What are the changes between this and the simple plugins example?

The main difference is that ``plugin`` decorator is associated with a
class and so is the resulting configuration, which gets stored as the
``plugins`` attribute of :attr:`dectate.App.config`. The other
difference is that we provide an ``identifier`` method in the action
definition. These differences support configuration *reuse*,
*conflicts*, *extension*, *overrides* and *isolation*.

Reuse
~~~~~

You can reuse configuration by simply subclassing ``MyApp``:

.. testcode::

  class SubApp(MyApp):
     pass

We commit both classes:

.. testcode::

  dectate.commit(MyApp, SubApp)

``SubClass`` now contains all the configuration declared for ``MyApp``:

  >>> sorted(SubApp.config.plugins.items())
  [('a', <function f at ...>), ('b', <function g at ...>)]

So class inheritance lets us reuse configuration, which allows
*extension* and *overrides*, which we discuss below.

Conflicts
~~~~~~~~~

Consider this example:

.. testcode::

   class ConflictingApp(MyApp):
       pass

   @ConflictingApp.plugin('foo')
   def f():
       pass

   @ConflictingApp.plugin('foo')
   def g():
       pass

Which function should be registered for ``foo``, ``f`` or ``g``? We should
refuse to guess and instead raise an error that the configuration is
in conflict. This is exactly what Dectate does:

.. doctest::

   >>> dectate.commit(ConflictingApp)
   Traceback (most recent call last):
     ...
   ConflictError: Conflict between:
    File "...", line 4
      @ConflictingApp.plugin('foo')
    File "...", line 8
      @ConflictingApp.plugin('foo')

As you can see, Dectate reports the lines in which the conflicting
configurations occurs.

How does Dectate know that these configurations are in conflict? This
is what the ``identifier`` method in our action definition did::

  def identifier(self, plugins):
      return self.name

We say here that the configuration is uniquely identified by its
``name`` attribute. If two configurations exist with the same name,
the configuration is considered to be in conflict.

Extension
~~~~~~~~~

When you subclass configuration, you can also *extend* ``SubApp`` with
additional configuration actions:

.. testcode::

  @SubApp.plugin('c')
  def h():
      pass # do something interesting

  dectate.commit(MyApp, SubApp)

``SubApp`` now has the additional plugin ``c``:

.. doctest::

  >>> sorted(SubApp.config.plugins.items())
  [('a', <function f at ...>), ('b', <function g at ...>), ('c', <function h at ...>)]

But ``MyApp`` is unaffected:

.. doctest::

  >>> sorted(MyApp.config.plugins.items())
  [('a', <function f at ...>), ('b', <function g at ...>)]

Overrides
~~~~~~~~~

What if you wanted to override a piece of configuration? You can do
this in ``SubApp`` by simply reusing the same ``name``:

.. testcode::

  @SubApp.plugin('a')
  def x():
      pass

  dectate.commit(MyApp, SubApp)

In ``SubApp`` we now have changed the configuration for ``a`` to
register the function ``x`` instead of ``f``. If we had done this for
``MyApp`` this would have been a conflict, but doing so in a subclass
lets you override configuration instead:

.. doctest::

  >>> sorted(SubApp.config.plugins.items())
  [('a', <function x at ...>), ('b', <function g at ...>), ('c', <function h at ...>)]

But ``MyApp`` still uses ``f``:

  >>> sorted(MyApp.config.plugins.items())
  [('a', <function f at ...>), ('b', <function g at ...>)]

Isolation
~~~~~~~~~

We have already seen in the inheritance and override examples that
``MyApp`` is isolated from configuration extension and overrides done
for ``SubApp``. We can in fact entirely isolate configuration from
each other.

We first set up a new base class with a directive, independently
from everything before:

.. testcode::

  class BaseApp(dectate.App):
      pass

  @BaseApp.directive('plugin')
  class PluginAction2(dectate.Action):
      config = {
         'plugins': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, plugins):
          return self.name

      def perform(self, obj, plugins):
          plugins[self.name] = obj

We don't set up any configuration for ``BaseApp``; it's intended to be
part of our framework. Now we create two subclasses:

.. testcode::

  class OneApp(BaseApp):
      pass

  class TwoApp(BaseApp):
      pass

As you can see ``OneApp`` and ``TwoApp`` are completely isolated from
each other; the only thing they share is a common ``BaseApp``.

We register a plugin for ``OneApp``:

.. testcode::

  @OneApp.plugin('a')
  def f():
      pass

This won't affect ``TwoApp`` in any way:

.. testcode::

  dectate.commit(OneApp, TwoApp)

.. doctest::

  >>> sorted(OneApp.config.plugins.items())
  [('a', <function f at ...>)]
  >>> sorted(TwoApp.config.plugins.items())
  []

``OneApp`` and ``TwoApp`` are isolated, so configurations are
independent, and cannot conflict or override.

The Anatomy of a Directive
--------------------------

Let's consider the directive registration again in detail::

  @MyApp.directive('plugin')
  class PluginAction(dectate.Action):
      config = {
         'plugins': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, plugins):
          return self.name

      def perform(self, obj, plugins):
          plugins[self.name] = obj

What is going on here?

* We create a new directive called ``plugin`` on ``MyApp``. It also
  exists for its subclasses.

* The directive is implemented with a custom class called
  ``PluginAction`` that inherits from :class:`dectate.Action`.

* ``config`` (:attr:`dectate.Action.config`) specifies that this
  directive has a configuration effect on ``plugins``. We declare that
  ``plugins`` is created using the ``dict`` factory, so our registry
  is a plain dictionary. You provide any factory function you like
  here.

* ``__init__`` specifies the parameters the directive should take and
  how to store them on the action object. You can use default
  parameters and such, but otherwise ``__init__`` should be very
  simple and not do any registration or validation. That logic should
  be in ``perform``.

* ``identifier`` (:meth:`dectate.Action.identifier`) takes the
  configuration objects specified by ``config`` as keyword
  arguments. It returns an immutable that is unique for this
  action. This is used to detect conflicts and determine how
  configurations override each other.

* ``perform`` (:meth:`dectate.Action.perform`) takes ``obj``, which is
  the function or class that the decorator is used on, and the
  arguments specified in ``config``. It should use ``obj`` and the
  information on ``self`` to configure the configuration objects.  In
  this case we store ``obj`` under the key ``self.name`` in the
  ``plugins`` dict.

Once we have declared the directive for our framework we can tell
programmers to use it.

Directives have absolutely no effect until *commit* is called, which
we do with ``dectate.commit``. This performs the actions and we can
then find the result ``MyApp.config`` (:attr:`dectate.App.config`).

The results are in ``MyApp.config.plugins`` as we set this up with
``config`` in our ``PluginAction``.

Depends
-------

In some cases you want to make sure that one type of directive has
been executed before the other -- the configuration of the second type
of directive depends on the former. You can make sure this happens by
using the ``depends`` (:attr:`dectate.Action.depends`) class
attribute.

First we set up a ``foo`` directive that registers into a ``foos``
dict:

.. testcode::

  class DependsApp(dectate.App):
      pass

  @DependsApp.directive('foo')
  class FooAction(dectate.Action):
      config = {
         'foos': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, foos):
          return self.name

      def perform(self, obj, foos):
          foos[self.name] = obj

Now we create a ``bar`` directive that depends on ``FooDirective`` and
uses information in the ``foos`` dict:

.. testcode::

   @DependsApp.directive('bar')
   class BarAction(dectate.Action):
      depends = [FooAction]

      config = {
         'foos': dict,  # also use the foos dict
         'bars': list
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, foos, bars):
          return self.name

      def perform(self, obj, foos, bars):
          in_foo = self.name in foos
          bars.append((self.name, obj, in_foo))

We have now ensured that ``BarAction`` actions are performed after
``FooAction`` action, no matter what order we use them:

.. testcode::

   @DependsApp.bar('a')
   def f():
       pass

   @DependsApp.bar('b')
   def g():
       pass

   @DependsApp.foo('a')
   def x():
       pass

   dectate.commit(DependsApp)

We expect ``in_foo`` to be ``True`` for ``a`` but to be ``False`` for
``b``:

.. doctest::

  >>> DependsApp.config.bars
  [('a', <function f at ...>, True), ('b', <function g at ...>, False)]

config dependencies
-------------------

In the example above, the items in ``bars`` depend on the items in ``foos``
and we've implemented this dependency in the ``perform`` of ``BarDirective``.

We can instead make the configuration object for the ``BarDirective``
depend on ``foos``. This way ``BarDirective`` does not need to know
about ``foos``. You can declare a dependency between config objects
with the ``factory_arguments`` attribute of the config factory. Any
config object that is created in earlier dependencies of this action,
or in the action itself, can be listed in ``factory_arguments``. The
key and value in ``factory_arguments`` have to match the key and value
in ``config`` of that earlier action.

First we create an app with a ``FooAction`` that sets up a ``foos``
config item as before:

.. testcode::

  class ConfigDependsApp(dectate.App):
      pass

  @ConfigDependsApp.directive('foo')
  class FooAction(dectate.Action):
      config = {
         'foos': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, foos):
          return self.name

      def perform(self, obj, foos):
          foos[self.name] = obj

Now we create a ``Bar`` class that also depends on the ``foos`` dict by
listing it in ``factory_arguments``:

.. testcode::

  class Bar(object):
      factory_arguments = {
          'foos': dict
      }

      def __init__(self, foos):
          self.foos = foos
          self.l = []

      def add(self, name, obj):
          in_foo = name in self.foos
          self.l.append((name, obj, in_foo))

We create a ``BarAction`` that depends on the ``FooAction`` (so that
``foos`` is created first) and that uses the ``Bar`` factory:

.. testcode::

   @ConfigDependsApp.directive('bar')
   class BarAction(dectate.Action):
      depends = [FooAction]

      config = {
         'bar': Bar
      }

      def __init__(self, name):
          self.name = name

      def identifier(self, bar):
          return self.name

      def perform(self, obj, bar):
          bar.add(self.name, obj)

When we use our directives:

.. testcode::

   @ConfigDependsApp.bar('a')
   def f():
       pass

   @ConfigDependsApp.bar('b')
   def g():
       pass

   @ConfigDependsApp.foo('a')
   def x():
       pass

   dectate.commit(ConfigDependsApp)

we get the same result as before:

.. doctest::

  >>> ConfigDependsApp.config.bar.l
  [('a', <function f at ...>, True), ('b', <function g at ...>, False)]

before and after
----------------

It can be useful to do some additional setup just before all actions
of a certain type are performed, or just afterwards. You can do this
using ``before`` (:meth:`dectate.Action.before`) and ``after``
(:meth:`dectate.Action.after`) static methods on the Action class:

.. testcode::

  class BeforeAfterApp(dectate.App):
      pass

  @BeforeAfterApp.directive('foo')
  class FooAction(dectate.Action):
      config = {
         'foos': list
      }
      def __init__(self, name):
          self.name = name

      @staticmethod
      def before(foos):
          print "before:", foos

      @staticmethod
      def after(foos):
          print "after:", foos

      def identifier(self, foos):
          return self.name

      def perform(self, obj, foos):
          foos.append((self.name, obj))

  @BeforeAfterApp.foo('a')
  def f():
      pass

  @BeforeAfterApp.foo('b')
  def g():
      pass

This executes ``before`` just before ``a`` and ``b`` are configured,
and then executes ``after``:

.. doctest::

  >>> dectate.commit(BeforeAfterApp)
  before: []
  after: [('a', <function f at ...>), ('b', <function g at ...>)]

grouping actions
----------------

Different actions normally don't conflict with each other. It can be
useful to group different actions together in a group so that they do
affect each other. You can do this with the ``group_class``
(:attr:`dectate.Action.group_class`) class attribute. Grouped classes
share their ``config`` and their ``before`` and ``after`` methods.

.. testcode::

  class GroupApp(dectate.App):
      pass

  @GroupApp.directive('foo')
  class FooAction(dectate.Action):
      config = {
         'foos': list
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, foos):
          return self.name

      def perform(self, obj, foos):
          foos.append((self.name, obj))

We now create a ``BarDirective`` that groups with ``FooAction``:

.. testcode::

  @GroupApp.directive('bar')
  class BarAction(dectate.Action):
     group_class = FooAction

     def __init__(self, name):
         self.name = name

     def identifier(self, foos):
         return self.name

     def perform(self, obj, foos):
         foos.append((self.name, obj))

It reuses the ``config`` from ``FooAction``. This means that ``foo``
and ``bar`` can be in conflict:

.. testcode::

  class GroupConflictApp(GroupApp):
      pass

  @GroupConflictApp.foo('a')
  def f():
      pass

  @GroupConflictApp.bar('a')
  def g():
      pass

.. doctest::

  >>> dectate.commit(GroupConflictApp)
  Traceback (most recent call last):
    ...
  ConflictError: Conflict between:
    File "...", line 4
      @GroupConflictApp.foo('a')
    File "...", line 8
      @GroupConflictApp.bar('a')

Additional discriminators
-------------------------

In some cases an action should conflict with *multiple* other actions
all at once. You can take care of this with the ``discriminators``
(:meth:`dectate.Action.discriminators`) method on your action:

.. testcode::

  class DiscriminatorsApp(dectate.App):
      pass

  @DiscriminatorsApp.directive('foo')
  class FooAction(dectate.Action):
      config = {
         'foos': dict
      }
      def __init__(self, name, extras):
          self.name = name
          self.extras = extras

      def identifier(self, foos):
          return self.name

      def discriminators(self, foos):
          return self.extras

      def perform(self, obj, foos):
          foos[self.name] = obj

An action now conflicts with an action of the same name *and* with
any action that is in the ``extra`` list:

.. testcode::

  # example
  @DiscriminatorsApp.foo('a', ['b', 'c'])
  def f():
      pass

  @DiscriminatorsApp.foo('b', [])
  def g():
      pass

And then:

.. doctest::

  >>> dectate.commit(DiscriminatorsApp)
  Traceback (most recent call last):
    ...
  ConflictError: Conflict between:
    File "...", line 2:
      @DiscriminatorsApp.foo('a', ['b', 'c'])
    File "...", line 6
      @DiscriminatorsApp.foo('b', [])

Composite actions
-----------------

When you can define an action entirely in terms of other actions, you
can subclass :class:`dectate.Composite`.

First we define a normal ``sub`` directive to use in the composite action
later:

.. testcode::

  class CompositeApp(dectate.App):
      pass

  @CompositeApp.directive('sub')
  class SubAction(dectate.Action):
      config = {
          'my': list
      }

      def __init__(self, name):
          self.name = name

      def identifier(self, my):
          return self.name

      def perform(self, obj, my):
          my.append((self.name, obj))

Now we can define a special :class:`dectate.Composite` subclass that
uses ``SubAction`` in an ``actions``
(:meth:`dectate.Composite.actions`) method:

.. testcode::

  @CompositeApp.directive('composite')
  class CompositeAction(dectate.Composite):
      def __init__(self, names):
          self.names = names

      def actions(self, obj):
          return [(SubAction(name), obj) for name in self.names]

We can now use it:

.. testcode::

  @CompositeApp.composite(['a', 'b', 'c'])
  def f():
      pass

  dectate.commit(CompositeApp)

And ``SubAction`` is performed three times as a result:

.. doctest::

  >>> CompositeApp.config.my
  [('a', <function f at ...>), ('b', <function f at ...>), ('c', <function f at ...>)]

``with`` statement
------------------

Sometimes you want to issue a lot of similar actions at once. You can
use the ``with`` statement to do so with less repetition:

.. testcode::

  class WithApp(dectate.App):
      pass

  @WithApp.directive('foo')
  class SubAction(dectate.Action):
      config = {
          'my': list
      }

      def __init__(self, a, b):
          self.a = a
          self.b = b

      def identifier(self, my):
          return (self.a, self.b)

      def perform(self, obj, my):
          my.append((self.a, self.b, obj))

Instead of this:

.. testcode::

  class VerboseWithApp(WithApp):
      pass

  @VerboseWithApp.foo('a', 'x')
  def f():
     pass

  @VerboseWithApp.foo('a', 'y')
  def g():
     pass

  @VerboseWithApp.foo('a', 'z')
  def h():
     pass

You can instead write:

.. testcode::

  class SuccinctWithApp(WithApp):
      pass

  with SuccinctWithApp.foo('a') as foo:
      @foo('x')
      def f():
          pass

      @foo('y')
      def g():
          pass

      @foo('z')
      def h():
          pass

And this has the same configuration effect:

.. doctest::

  >>> dectate.commit(VerboseWithApp, SuccinctWithApp)
  >>> VerboseWithApp.config.my
  [('a', 'x', <function f at ...>), ('a', 'y', <function g at ...>), ('a', 'z', <function h at ...>)]
  >>> SuccinctWithApp.config.my
  [('a', 'x', <function f at ...>), ('a', 'y', <function g at ...>), ('a', 'z', <function h at ...>)]

importing recursively
---------------------

When you use dectate-based decorators across a package, it can be
useful to just import *all* modules in it at once. This way the user
cannot forget to import a module with decorators in it.

Dectate itself does not offer this facility, but you can use the
importscan_ library to do this recursive import. Simply do something
like::

  import my_package

  importscan.scan(my_package, ignore=['.tests'])

This imports every module in ``my_package``, except for the ``tests``
sub package.

.. _importscan: http://importscan.readthedocs.io/en/latest/

logging
-------

Dectate logs information about the performed actions as debug log
messages. By default this goes to the
``dectate.directive.<directive_name>`` log. You can use the standard
Python :mod:`logging` module function to make this information go
to a log file.

If you want to override the name of the log you can set
``logger_name`` (:attr:`dectate.App.logger_name`) on the app class::

  class MorepathApp(dectate.App):
     logger_name = 'morepath.directive'

querying
--------

Dectate keeps a database of committed actions that can be queried by
using :class:`dectate.Query`.

Here is an example of a query for all the plugin actions on ``MyApp``:

.. testcode::

  q = dectate.Query('plugin')

We can now run the query:

.. doctest::
  :options: +NORMALIZE_WHITESPACE

  >>> list(q(MyApp))
  [(<PluginAction ...>, <function f ...>),
   (<PluginAction ...>, <function g ...>)]

We can also filter the query for attributes of the action:

.. doctest::

  >>> list(q.filter(name='a')(MyApp))
  [(<PluginAction object ...>, <function f ...>)]

Sometimes the attribute on the action is not the same as the name you
may want to use in the filter. You can use
:attr:`dectate.Action.filter_name` to create a mapping to the correct
attribute.

By default the filter does an equality comparison. You can define your
own comparison function for an attribute using
:attr:`dectate.Action.filter_compare`.

If you want to allow a query on a :class:`Composite` action you need
to give it some help by defining
xs:attr:`dectate.Composite.query_classes`.

.. _query_tool:

query tool
----------

Dectate also includes a command-line tool that lets you issue queries. You
need to configure it for your application. For instance, in the module
``main.py`` of your project::

  import dectate

  def query_tool():
      # make sure to scan or import everything needed at this point
      dectate.query_tool(SomeApp.commit())

In this function you should commit any :class:`dectate.App` subclasses
your application normally uses, and then provide an iterable of them
to :func:`dectate.query_tool`. These are the applications that are
queried by default if you don't specify ``--app``. We do it all in one
here as we can get the app class that were committed from the result
of :meth:`App.commit`.

Then in ``setup.py`` of your project::

    entry_points={
        'console_scripts': [
            'decq = query.main:query_tool',
        ]
    },

When you re-install this project you have a command-line tool called
``decq`` that lets you issues queries. For instance, this query
returns all uses of directive ``foo`` in the apps you provided to
``query_tool``::

  $ decq foo
  App: <class 'query.a.App'>
    File ".../query/b.py", line 4
    @App.foo(name='alpha')

    File ".../query/b.py", line 9
    @App.foo(name='beta')

    File ".../query/b.py", line 14
    @App.foo(name='gamma')

    File ".../query/c.py", line 4
    @App.foo(name='lah')

  App: <class 'query.a.Other'>
    File ".../query/b.py", line 19
    @Other.foo(name='alpha')

And this query filters by ``name``::

  $ decq foo name=alpha
  App: <class 'query.a.App'>
    File ".../query/b.py", line 4
    @App.foo(name='alpha')

  App: <class 'query.a.Other'>
    File ".../query/b.py", line 19
    @Other.foo(name='alpha')

You can also explicit provide the app classes to query with the
``--app`` option; the default list of app classes is ignored in this
case::

  $ bin/decq --app query.a.App foo name=alpha
  App: <class 'query.a.App'>
    File ".../query/b.py", line 4
    @App.foo(name='alpha')

You need to give ``--app`` a dotted name of the :class:`dectate.App`
subclass to query. You can repeat the ``--app`` option to query
multiple apps.

Not all things you would wish to query on are string attributes.  You
can provide a conversion function that takes the string input and
converts it to the underlying object you want to compare to using
:attr:`dectate.Action.filter_convert`.

A working example is in ``scenarios/query`` of the Dectate project.

Sphinx Extension
----------------

If you use Sphinx_ to document your project and you use the
``sphinx.ext.autodoc`` extension to document your API, you need to
install a Sphinx extension so that directives are documented
properly. In your Sphinx ``conf.py`` add ``'dectate.sphinxext'`` to
the ``extensions`` list.

.. _Sphinx: http://www.sphinx-doc.org

``__main__`` and conflicts
--------------------------

.. sidebar:: Import-time side effects are evil

   This scenario is based on the one described in `Application
   programmers don't control the module-scope codepath`_ in the
   Pyramid design defense document. If you're curious, look under
   ``scenarios/main_module`` in the Dectate project for a Dectate
   version.

   Dectate makes a different compromise than Venusian -- it reports an
   error if a directive is executed because of a double import, so it
   won't get you into trouble. But since Dectate's directives cause
   registrations to happen immediately (but defer configuration), you
   can dynamically generate them inside Python function, which won't
   work with with Venusian.

   .. _`Application programmers don't control the module-scope codepath`: http://docs.pylonsproject.org/projects/pyramid/en/latest/designdefense.html#application-programmers-don-t-control-the-module-scope-codepath-import-time-side-effects-are-evil

In certain scenarios where you run your code like this::

  $ python app.py

and you use ``__name__ == '__main__'`` to determine whether the module
should run::

  if __name__ == '__main__':
      import another_module
      dectate.commit(App)

you might get a :exc:`ConflictError` from Dectate that looks somewhat
like this::

  Traceback (most recent call last):
   ...
  dectate.error.ConflictError: Conflict between:
    File "/path/to/app.py", line 6
      @App.foo(name='a')
    File "app.py", line 6
      @App.foo(name='a')

The same line shows up on *both* sides of the configuration conflict,
but the path is absolute on one side and relative on the other.

This happens because in some scenarios involving ``__main__``, Python
imports a module *twice* (`more about this`_). Dectate refuses to
operate in this case until you change your imports so that this
doesn't happen anymore.

.. _`more about this`: http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#executing-the-main-module-twice

How to avoid this scenario? If you use setuptools `automatic script
creation`_ this problem is avoided entirely.

.. _`automatic script creation`: https://pythonhosted.org/setuptools/setuptools.html#automatic-script-creation

.. sidebar:: Fooling Dectate after all

  It *is* possible to fool Dectate into accepting a double import
  without conflicts, but you'd need to work hard. You need to use a
  global variable that gets modified during import time and then use
  it as a directive argument. If you want to dynamically generate
  directives then don't do that in module-scope -- do it in a function.

If you want to use the ``if __name__ == '__main__'`` system, keep your
main module tiny and just import the main function you want to run
from elsewhere.

So, Dectate warns you if you do it wrong, so don't worry about it.
