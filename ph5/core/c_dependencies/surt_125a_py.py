
from distutils.core import setup, Extension
import os
import numpy


def install():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    setup(name="rt_125a_py",
          version="2010.169",
          include_dirs=[numpy.get_include()],
          ext_modules=[Extension("rt_125a_py",
                                 ["{0}/rt_125a_py.c".format(dir_path),
                                  "{0}/rt_125awrapper_py.c"
                                  .format(dir_path)],)])


if __name__ == '__main__':
    install()
