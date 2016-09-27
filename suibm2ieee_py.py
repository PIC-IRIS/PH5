
from distutils.core import setup, Extension
import numpy

setup (name = "ibm2iee_py", version = "2013.121", include_dirs = [numpy.get_include()],
       ext_modules = [
    Extension (
    "ibm2ieee_py", ["ibm2ieee_py.c", "ibm2ieeewrapper_py.c"],
    #extra_link_args = ["-m32"]
)])
