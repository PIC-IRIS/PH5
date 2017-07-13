
from distutils.core import setup, Extension
import os
import numpy


def install():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    setup (name = "bcd_py", version = "2014.119", include_dirs = [numpy.get_include()],
           ext_modules = [
        Extension (
        "bcd_py", ["{0}/bcd_py.c".format(dir_path),
                   "{0}/bcdwrapper_py.c".format(dir_path)],
        #extra_link_args = ["-m32"]
    )])


if __name__ == '__main__':
    install()
