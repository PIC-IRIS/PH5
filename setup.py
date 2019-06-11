"""A setuptools module for PH5.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from __future__ import (print_function)

# install C dependencies
from ph5.core.c_dependencies import subcd_py
from ph5.core.c_dependencies import sufirfilt_py
from ph5.core.c_dependencies import suibm2ieee_py
from ph5.core.c_dependencies import surt_125a_py
from ph5.core.c_dependencies import surt_130_py

# Always prefer setuptools over distutils
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
from setuptools.command.develop import develop
from distutils import log

# Importing setuptools monkeypatches some of distutils commands so things like
# 'python setup.py develop' work. Wrap in try/except so it is not an actual
# dependency. Inplace installation with pip works also without importing
# setuptools.
try:
    import setuptools  # @UnusedImport # NOQA
except ImportError:
    pass

try:
    import PyQt4
except ImportError:
    msg = ("No module named PyQt4. "
           "Please install PyQt4 first, it is needed before installing PH5. "
           "\n\n"
           "If using Anaconda run 'conda install pyqt=4'"
           "For pip users, PyQt4 installation instructions are available at "
           "http://pyqt.sourceforge.net/Docs/PyQt4/installation.html.")
    raise ImportError(msg)

try:
    import PySide
except ImportError:
    msg = ("No module named PySide. "
           "Please install PySide first, it is needed before installing PH5. "
           "\n\n"
           "If using Anaconda run 'conda install PySide'"
           "For pip users, PySide installation instructions are available at "
           "https://pypi.org/project/PySide/#installation.")
    raise ImportError(msg)

try:
    import numpy  # @UnusedImport # NOQA
except ImportError:
    msg = ("No module named numpy. "
           "Please install numpy first, it is needed before installing PH5.")
    raise ImportError(msg)


from ph5.entry_points import CommandList


command_list = CommandList()

setup(
    name="ph5",
    version="4.1.2_2",
    # metadata for upload to PyPI
    author="IRIS PASSCAL Instrument Center",
    author_email="dhess@passcal.nmt.edu",
    description="A library of PH5 APIs",
    license="MIT",
    keywords="ph5 IRIS miniSEED sac segy seg-y segd seg-d",
    url="https://github.com/PIC-IRIS/PH5/",   # project home page, if any
    install_requires=[
                      'six',
                      'Cython',
                      'nose',
                      'numpy',
                      'numexpr',
                      'pyproj',
                      'psutil',
                      'obspy',
                      'vispy',
                      'lxml',
                      'construct==2.5.1',
                      'simplekml',
                      'tables',
                      'matplotlib<2',
                      'subprocess32'
                      #pyicu - seems to work without
                      #pyqt4 - required external program
                      #PySide - required external program
                     ],
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        
        # Indicate who your project is intended for
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'Topic :: Scientific/Engineering :: Physics',
        
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',
        
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',    
    ],
    entry_points = {group: [ep.get_entry_point_str() for ep in eps]
                        for group, eps in command_list.entrypoints.items()}, 
    packages=['ph5',
              'ph5/clients',
              'ph5/clients/ph5view',
              'ph5/core',
              'ph5/core/c_dependencies',
              'ph5/utilities'],
    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'utilities': ['Event.cfg', 'Receiver.cfg'],
        'clients': ['PH5Viewer.cfg'],
        'ph5/core/c_dependencies':
                    ['bcd_py.cd', 'bcdwrapper_py.c',
                     'firfilt_py.c', 'firfiltwrapper_py.c', 'fir.h',
                     'ibm2ieee_py.c', 'ibm2ieeewrapper_py.c',
                     'rt_125a_py.c', 'rt_125awrapper_py.c',
                     'rt_130_py.c', 'rt_130wrapper_py.c', 'rt_130_py.h'
                     ]
    },
    # install c-dependencies
    ext_modules=[Extension(*subcd_py.get_extension_options(),
                           include_dirs=[numpy.get_include()]),
                 Extension(*sufirfilt_py.get_extension_options(),
                           include_dirs=[numpy.get_include()]),
                 Extension(*suibm2ieee_py.get_extension_options(),
                           include_dirs=[numpy.get_include()]),
                 Extension(*surt_125a_py.get_extension_options(),
                           include_dirs=[numpy.get_include()]),
                 Extension(*surt_130_py.get_extension_options(),
                           include_dirs=[numpy.get_include()])]
)

