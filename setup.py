"""A setuptools module for PH5.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from __future__ import (print_function)

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
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

setup(
    name="ph5",
    version="4.0.0",

    # metadata for upload to PyPI
    author="IRIS PASSCAL Instrument Center",
    author_email="dhess@passcal.nmt.edu",
    description="A library of PH5 APIs",
    license="MIT",
    keywords="ph5 IRIS miniSEED sac",
    url="https://github.com/PIC-IRIS/PH5/",   # project home page, if any
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
      
    scripts = ['ph5/clients/PH5View/PH5ViewerwVispyAPI.py',
               'ph5/clients/ph5toevt.py',
               'ph5/clients/ph5tomsAPI.py',
               'ph5/clients/ph5torec.py',
               'ph5/clients/ph5tostationxml.py',
               'ph5/utilities/125a2ph5.py',
               'ph5/utilities/1302ph5.py',
               'ph5/utilities/KefEdit.py',
               'ph5/utilities/cross_check_event_array_data.py',
               'ph5/utilities/dumpfair.py',
               'ph5/utilities/dumpsac.py',
               'ph5/utilities/dumpsgy.py',
               'ph5/utilities/fix_3chan_texan.py',
               'ph5/utilities/fix_num_samples.py',
               'ph5/utilities/geod2kef.py',
               'ph5/utilities/grao2ph5.py',
               'ph5/utilities/index_offset_t.py',
               'ph5/utilities/initialize-ph5.py',
               'ph5/utilities/kef2kml.py',
               'ph5/utilities/kef2ph5.py',
               'ph5/utilities/kmz-builder.py',
               'ph5/utilities/load_Das_t.py',
               'ph5/utilities/meta-data-gen.py',
               'ph5/utilities/novenGUI.py',
               'ph5/utilities/nuke-table.py',
               'ph5/utilities/pformaCL.py',
               'ph5/utilities/pformaGUI.py',
               'ph5/utilities/ph5_merge_helper.py',
               'ph5/utilities/ph5_total.py',
               'ph5/utilities/recreate_external_references.py',
               'ph5/utilities/report2ph5.py',
               'ph5/utilities/seg2toph5.py',
               'ph5/utilities/segd2ph5.py',
               'ph5/utilities/segy2ph5.py',
               'ph5/utilities/set_deploy_pickup_times.py',
               'ph5/utilities/set_n_i_response.py',
               'ph5/utilities/sort-kef-gen.py',
               'ph5/utilities/sort-recv-kef.py',
               'ph5/utilities/sort-shot-kef.py',
               'ph5/utilities/sort_array_t.py',
               'ph5/utilities/tabletokef.py',
               'ph5/utilities/time-kef-gen.py',
               'ph5/utilities/unsimpleton.py'],

    packages=['ph5', 'ph5/clients', 'ph5/core', 'ph5/utilities'],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'utilities': ['Event.cfg', 'Receiver.cfg'],
        'clients': ['PH5Viewer.cfg'],
    },
    
)

