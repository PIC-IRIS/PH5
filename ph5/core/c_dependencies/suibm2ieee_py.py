
from distutils.core import setup, Extension
import os
import numpy


def install():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    setup(name="ibm2iee_py", version="2013.121", include_dirs=[numpy.get_include()],
          ext_modules=[
        Extension(
            "ibm2ieee_py", ["{0}/ibm2ieee_py.c".format(dir_path),
                            "{0}/ibm2ieeewrapper_py.c".format(dir_path)],
            #extra_link_args = ["-m32"]
        )])


if __name__ == '__main__':
    install()
