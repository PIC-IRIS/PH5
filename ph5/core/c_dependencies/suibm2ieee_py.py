from distutils.core import setup, Extension
import os


try:
    import numpy  # @UnusedImport # NOQA
except ImportError:
    msg = ("No module named numpy. "
           "Please install numpy first, it is needed before installing PH5.")
    raise ImportError(msg)


def get_extension_options():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    options = ("ibm2ieee_py",
               ["ph5/core/c_dependencies/ibm2ieee_py.c",
                "ph5/core/c_dependencies/ibm2ieeewrapper_py.c"])
    return options


def install():
    setup (name="ibm2iee_py",
           version="2013.121",
           ext_modules=[Extension(*get_extension_options(),
                                  include_dirs=[numpy.get_include()]
                                  )])


if __name__ == '__main__':
    install()
