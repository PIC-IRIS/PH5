from distutils.core import setup, Extension

try:
    import numpy  # @UnusedImport # NOQA
except ImportError:
    msg = ("No module named numpy. "
           "Please install numpy first, it is needed before installing PH5.")
    raise ImportError(msg)


def get_extension_options():
    options = ("firfilt_py",
               ["ph5/core/c_dependencies/firfilt_py.c",
                "ph5/core/c_dependencies/firfiltwrapper_py.c"])
    return options


def install():
    setup(name="firfilt_py",
          version="2010.153",
          ext_modules=[Extension(*get_extension_options(),
                                 include_dirs=[numpy.get_include()]
                                 )])


if __name__ == '__main__':
    install()
