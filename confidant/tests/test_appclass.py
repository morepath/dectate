import venusian
from .. import appclass


def test_registry():

    class MyApp(appclass.App):
        pass

    assert isinstance(MyApp.confidant_registry, appclass.Registry)
    assert MyApp.confidant_registry is not appclass.App.confidant_registry


def test_custom_registry():

    class MyRegistry(appclass.Registry):
        pass

    class MyApp(appclass.App):
        confidant_registry_factory = MyRegistry

    assert isinstance(MyApp.confidant_registry, MyRegistry)


def test_core_app():
    assert isinstance(appclass.App.confidant_registry, appclass.Registry)


def test_testing_config():
    class MyApp(appclass.App):
        confidant_testing_config = 'foo'

    assert MyApp.confidant_registry.testing_config == 'foo'


def test_venusian_callback():
    class DummyConfig(object):
        def __init__(self):
            self.classes = []

        def appclass(self, cls):
            self.classes.append(cls)

    config = DummyConfig()
    scanner = venusian.Scanner(config=config)
    from .fixture import appclass_venusian
    scanner.scan(appclass_venusian)

    assert config.classes == [appclass_venusian.MyApp]

