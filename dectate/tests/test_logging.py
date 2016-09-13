import logging
from dectate.app import App, directive
from dectate.config import Action, commit


class Handler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(Handler, self).__init__(level)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_intercept_logging():
    log = logging.getLogger('my_logger')

    test_handler = Handler()

    log.addHandler(test_handler)
    # default is NOTSET which would propagate log to parent
    # logger instead of handling it directly.
    log.setLevel(logging.DEBUG)
    log.debug("This is a log message")

    assert len(test_handler.records) == 1
    assert test_handler.records[0].getMessage() == 'This is a log message'


def test_simple_config_logging():
    log = logging.getLogger('dectate.directive.foo')

    test_handler = Handler()

    log.addHandler(test_handler)
    log.setLevel(logging.DEBUG)

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

    messages = [r.getMessage() for r in test_handler.records]
    assert len(messages) == 1
    expected = (
        "@dectate.tests.test_logging.MyApp.foo('hello') "
        "on dectate.tests.test_logging.f")

    assert messages[0] == expected


def test_subclass_config_logging():
    log = logging.getLogger('dectate.directive.foo')

    test_handler = Handler()

    log.addHandler(test_handler)
    log.setLevel(logging.DEBUG)

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

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp, SubApp)

    messages = [r.getMessage() for r in test_handler.records]
    assert len(messages) == 2
    expected = (
        "@dectate.tests.test_logging.MyApp.foo('hello') "
        "on dectate.tests.test_logging.f")

    assert messages[0] == expected

    expected = (
        "@dectate.tests.test_logging.SubApp.foo('hello') "
        "on dectate.tests.test_logging.f "
        "(from dectate.tests.test_logging.MyApp)")

    assert messages[1] == expected


def test_override_logger_name():
    log = logging.getLogger('morepath.directive.foo')

    test_handler = Handler()

    log.addHandler(test_handler)
    log.setLevel(logging.DEBUG)

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
        logger_name = 'morepath.directive'

        foo = directive(MyDirective)

    @MyApp.foo('hello')
    def f():
        pass

    commit(MyApp)

    messages = [r.getMessage() for r in test_handler.records]
    assert len(messages) == 1
    expected = (
        "@dectate.tests.test_logging.MyApp.foo('hello') "
        "on dectate.tests.test_logging.f")

    assert messages[0] == expected
