from distutils.core import setup, Extension


def get_extension_options():
    options = ("mseed_py",
               ["ph5/core/c_dependencies/mseedwrapper_py.c"])
    return options


def install():
    setup(name="mseed_py",
          version="2019.139",
          ext_modules=[Extension(*get_extension_options())])


if __name__ == '__main__':
    install()

