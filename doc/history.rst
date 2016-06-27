History of Dectate
==================

Dectate was extracted from Morepath and then extensively refactored
and cleaned up. It is authored by me, Martijn Faassen.

In the beginning (around 2001) there was `zope.configuration`_, part of
the Zope 3 project. It features declarative XML configuration with
conflict detection and overrides to assemble pieces of Python code.

.. _`zope.configuration`: https://pypi.python.org/pypi/zope.configuration

In 2006, I helped create the Grok project. This did away with the XML
based configuration and instead used Python code. This in turn then
drove `zope.configuration`. Grok did not use Python decorators but
instead used specially annotated Python classes, which were
recursively scanned from modules. Grok's configuration system was spun
off as the Martian_ library.

.. _Martian: https://pypi.python.org/pypi/martian

Chris McDonough was then inspired by Martian to create Venusian_, a
deferred decorator execution system. It is like Martian in that it
imports Python modules recursively in order to find configuration.

.. _Venusian: https://pypi.python.org/pypi/venusian

I created the Morepath_ web framework, which uses decorators for
configuration throughout and used Venusian. Morepath grew a
configuration subsystem where configuration is associated with
classes, and uses class inheritance to power configuration reuse and
overrides. This configuration subsystem started to get a bit messy
as requirements grew.

.. _Morepath: http://morepath.readthedocs.io

So in 2016 I extracted the configuration system from Morepath into its
own library, Dectate. This allowed me to extensively refactor the code
for clarity and features. Dectate does not use Venusian for
configuration. Dectate still defers the execution of configuration
actions to an explicit commit phase, so that conflict detection and
overrides and such can take place.
