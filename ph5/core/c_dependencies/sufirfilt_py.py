
#   Run with pnpython2
from distutils.core import setup, Extension
import os
import numpy


def install():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    setup(name="firfilt_py",
          version="2010.153",
          include_dirs=[numpy.get_include()],
          ext_modules=[Extension("firfilt_py",
                                 ["{0}/firfilt_py.c".format(dir_path),
                                  "{0}/firfiltwrapper_py.c"
                                  .format(dir_path)],)])


if __name__ == '__main__':
    install()
