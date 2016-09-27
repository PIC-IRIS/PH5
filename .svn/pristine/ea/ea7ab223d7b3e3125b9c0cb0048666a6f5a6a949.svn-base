
from distutils.core import setup, Extension
import numpy

setup (name = "bcd_py", version = "2014.119", include_dirs = [numpy.get_include()],
       ext_modules = [
    Extension (
    "bcd_py", ["bcd_py.c", "bcdwrapper_py.c"],
    #extra_link_args = ["-m32"]
)])
