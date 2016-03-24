Using Dectate
=============

Introduction
------------

We say Dectate is a configuration system for Python, but what do we
mean by that? *Configuration* in this context is the process of
connecting pieces of code together into an application. Some examples
of code configuration are declaring routes, assembling middleware and
declaring views for models. What code configuration you need is
determined by you, the framework author.

Features
--------

* Decorator-based configuration -- users declare things by using Python
  decorators on functions and classes: we call these *directives*,
  which issue configuration *actions*.

* Dectate detects conflicts between pieces of configuration in user
  code and reports what pieces of code are in conflict.

* Users can easily reuse and extend configuration: it's just Python
  class inheritance.

* Users can easily override configurations.

* Unlike normal decorators, configuration actions aren't performed
  immediately when a module is imported. Instead configuration actions
  are executed only when the user explicitly *commits* the
  configuration.

* You can control the order in which configuration actions are
  executed. This is unrelated to where the user uses the directives in
  code. You do this by declaring *dependencies* between types of
  configuration actions.

* You can declare exactly what registries are used by a type of
  configuration action -- different types of actions can use
  different registries.

* You can compose configuration actions from other, simpler ones.

* Dectate-based configuration systems are themselves easily extensible
  with new directives.

App classes
-----------

Configuration in Dectate is associated with special *classes* which need
to derive from :class:`dectate.App`:

.. testcode::

  import dectate

  class MyApp(dectate.App):
      pass

Creating a directive
--------------------

We can now use the :meth:`dectate.App.directive` decorator We need to
declare a *directive* which executes a special configuration action:

.. testcode::

  @MyApp.directive('register')
  class RegisterAction(dectate.Action):
      config = {
         'registry': dict
      }
      def __init__(self, name):
          self.name = name

      def identifier(self, registry):
          return self.name

      def perform(self, obj, registry):
          registry[self.name] = obj

Let's use it now:

.. testcode::

  @MyApp.register('a')
  def f():
      pass # do something interesting

  @MyApp.register('b')
  def g():
      pass # something else interesting

We have registered the function ``f`` on ``MyApp``. The ``name``
argument is ``'a'``. We've registered ``g`` under ``'b'``.

We can now commit the configuration for ``MyApp``:

.. testcode::

  dectate.commit([MyApp])

We can now take a look at the configuration:

.. doctest::

  >>> MyApp.config.registry
  {'a': <function f at ...>, 'b': <function g at ...>}

What is going on here?

* We create a new directive called ``register`` on ``MyApp`` and
  its subclasses.

* The directive is implemented with a custom class called
  ``RegisterAction`` that inherits from :class:`dectate.Action`.

* ``config`` specifies that this directive has a configuration effect
  on ``registry``. We declare that ``registry`` is created using
  a ``dict``, so our registry is a plain dictionary. You provide
  any factory function you like here.

* ``__init__`` specifies the parameters the directive should take and how
  to store them on the action object.

* ``identifier`` takes the configuration objects specified by ``config``
  as arguments. It should return an immutable that is unique for
  this action. This is used to detect conflicts and determine overrides.

* ``perform`` takes ``obj``, which is the function or class that is
  being decorated, and a list of config objects. It should use ``obj`` and the
  information on ``self`` to configure the configuration objects.
  In this case we store ``obj`` under the key ``self.name`` in the
  ``registry`` dict.

Once we have declared the directive for our framework we can tell
programmers to use it.

Directives have absolutely no effect until *commit* is called, which
we did with ``dectate.commit``. This performs the actions and we can
then find the result ``MyApp.config``.

The results are in ``MyApp.config.registry`` as we set this up with
``config`` in our ``RegisterAction``.
