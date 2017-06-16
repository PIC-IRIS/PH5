
#   Run with pnpython2
from distutils.core import setup, Extension
import numpy

setup (name = "firfilt_py", version = "2010.153", include_dirs = [numpy.get_include()],
       ext_modules = [
    Extension (
    "firfilt_py", ["firfilt_py.c", "firfiltwrapper_py.c"],
    #extra_link_args = ["-m32"]
)])
