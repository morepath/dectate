Using Dectate
=============

Introduction
------------

We say Dectate is a configuration system for Python, but what do we
mean by that? *Configuration* in this context is the process of
connecting pieces of code together into an application. Some examples
of code configuration are declaring routes, assembling middleware and
declaring views for models.

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
