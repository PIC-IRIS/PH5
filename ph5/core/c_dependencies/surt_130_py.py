
from distutils.core import setup, Extension
import os
import numpy


def install():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    setup(name="rt_130_py",
          version="2001.273",
          include_dirs=[numpy.get_include()],
          ext_modules=[Extension("rt_130_py",
                                 ["{0}/rt_130_py.c".format(dir_path),
                                  "{0}/rt_130wrapper_py.c"
                                  .format(dir_path)],)])


if __name__ == '__main__':
    install()
