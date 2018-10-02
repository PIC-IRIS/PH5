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
    entry_points = {
        'gui_scripts': [
            'ph5view = ph5.clients.ph5view.ph5_viewer:startapp',
            'noven = ph5.utilities.noven:startapp',
            'pforma = ph5.utilities.pformagui:startapp',
            'kefedit = ph5.utilities.kefedit:startapp',
            'experiment_t_gen = ph5.utilities.changes:startapp',
        ],
        'console_scripts': [
            # clients
            'ph5toevt = ph5.clients.ph5toevt:main',
            'ph5toms = ph5.clients.ph5toms:main',
            'ph5torec = ph5.clients.ph5torec:main',
            'ph5tostationxml = ph5.clients.ph5tostationxml:main',
            'ph5toexml = ph5.clients.ph5toexml:main',
            # utilities
            '125atoph5 = ph5.utilities.125a2ph5:main',
            '130toph5 = ph5.utilities.1302ph5:main',
            'cross_check_event_array_data = ph5.utilities.cross_check_event_array_data:main',
            'csvtokef = ph5.utilities.csvtokef:main',
            'dumpfair = ph5.utilities.dumpfair:main',
            'dumpsac = ph5.utilities.dumpsac:main',
            'dumpsgy = ph5.utilities.dumpsgy:main',
            'fix_3chan_texan = ph5.utilities.fix_3chan_texan:main',
            'fix_num_samples = ph5.utilities.fix_num_samples:main',
            'geo_kef_gen = ph5.utilities.geod2kef:main',
            'graotoph5 = ph5.utilities.grao2ph5:main',
            'index_offset_t = ph5.utilities.index_offset_t:main',
            'initialize_ph5 = ph5.utilities.initialize_ph5:main',
            'keftocsv = ph5.utilities.keftocsv:main',
            'keftokml = ph5.utilities.kef2kml:main',
            'keftoph5 = ph5.utilities.kef2ph5:main',
            'load_das_t = ph5.utilities.load_das_t:main',
            'meta_data_gen = ph5.utilities.meta_data_gen:main',
            'nuke_table = ph5.utilities.nuke_table:main',
            'delete_table = ph5.utilities.nuke_table:main',
            'pformacl = ph5.utilities.pformacl:main',
            'ph5_merge_helper = ph5.utilities.ph5_merge_helper:main',
            'ph5_total = ph5.utilities.ph5_total:main',
            'ph5_validate = ph5.utilities.ph5validate:main',
            'recreate_external_references = ph5.utilities.recreate_external_references:main',
            'reporttoph5 = ph5.utilities.report2ph5:main',
            'resp_load = ph5.utilities.resp_load:main',
            'seg2toph5 = ph5.utilities.seg2toph5:main',
            'segdtoph5 = ph5.utilities.segd2ph5:main',
            'segytoph5 = ph5.utilities.segy2ph5:main',
            'set_deploy_pickup_times = ph5.utilities.set_deploy_pickup_times:main',
            'set_n_i_response = ph5.utilities.set_n_i_response:main',
            'sort_kef_gen = ph5.utilities.sort_kef_gen:main',
            'sort_array_t = ph5.utilities.sort_array_t:main',
            'ph5tokef = ph5.utilities.tabletokef:main',
            'time_kef_gen = ph5.utilities.time_kef_gen:main',
            'tabletokef = ph5.utilities.tabletokef:main',
            'unsimpleton = ph5.utilities.unsimpleton:main',
        ],
    },
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

