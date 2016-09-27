
from distutils.core import setup, Extension
import numpy

setup (name = "rt_125a_py", version = "2010.169", include_dirs = [numpy.get_include()],
       ext_modules = [
    Extension (
    "rt_125a_py", ["rt_125a_py.c", "rt_125awrapper_py.c"],
    #extra_link_args = ["-m32"]
)])
