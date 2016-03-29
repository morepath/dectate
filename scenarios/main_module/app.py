from config import App
import pprint
import dectate
import app2  # noqa


@App.foo(name='a')
def f():
    pass

if __name__ == '__main__':
    dectate.commit([App])
    pprint.pprint(App.config.my)
