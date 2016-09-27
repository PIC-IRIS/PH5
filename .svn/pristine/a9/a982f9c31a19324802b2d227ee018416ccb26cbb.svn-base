
from distutils.core import setup, Extension
import numpy

setup (name = "rt_130_py", version = "2001.273", include_dirs = [numpy.get_include()],
       ext_modules = [
    Extension (
    "rt_130_py", ["rt_130_py.c", "rt_130wrapper_py.c"],
    #extra_link_args = ["-m32"]
)])
