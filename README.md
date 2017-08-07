# PH5 
[![Build Status](https://travis-ci.org/PIC-IRIS/PH5.svg?branch=master)](https://travis-ci.org/PIC-IRIS/PH5) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/ph5.svg)](https://pypi.python.org/pypi/ph5/)[![PyPI Version](https://img.shields.io/pypi/v/ph5.svg)](https://pypi.python.org/pypi/ph5)

A library of command line utilities and APIs for building and interacting with PH5 datasets. 

**See the [PH5 Wiki](https://github.com/PIC-IRIS/PH5/wiki) for information about the sturcuture and use of PH5**

# Detailed Installation Instructions

The easiest way to install PH5 is to use the Anaconda distribution of python. These instructions
only cover installation of PH5 dependencies using Anaconda. This is because PH5 (and many python tools) require packages (aka modules) that have C dependencies.

## Anaconda
Anaconda is not an absolute requirement to get PH5 to work. As long as you can get the necessary python dependencies installed, PH5 will work. If you want to install Anaconda (highly recommended), follow the Mac or Linux instructions below.

### Mac
After downloading the Anaconda version 2.7 installer from https://www.continuum.io/downloads, double click the .pkg file and follow the instructions on the screen. Use all of the defaults for installation.

### Linux
After downloading the Anaconda version 2.7 installer from https://www.continuum.io/downloads execute the associated shell script. For example, if the file downloaded were named Anaconda2-4.4.0-Linux-x86_64.sh you would run `bash Anaconda2-4.4.0-Linux-x86_64.sh` in the directory where you downloaded the file.

## Installing PH5
Below are instructions for installing PH5 with Anaconda. PH5 has several [system requirements](https://github.com/PIC-IRIS/PH5/wiki/PH5-Requirements) that are necessary for installation. If you are using Anaconda these system requirements are pre-installed with Anaconda, making for a much simpler installation.

### Installing PH5 from source
* Open a terminal.
* Clone the PH5 project from GitHub to your local machine by running `git clone https://github.com/PIC-IRIS/PH5.git` or downloading the zip file from the main github page .
* Add the conda-forge channel to your Anaconda configuration by running `conda config --add channels conda-forge`
* Create a new Anaconda Virtual Environment for ph5 by running `conda create -q --name=ph5 python=2.7`
* Install PH5 dependencies into the environment by running `conda env update --name=ph5 -f=/path/to/ph5/environment.yml`
* Source the newly created ph5 environment by running `source activate ph5`
* Install the PH5 python package by running `python setup.py install` in the cloned PH5 project root directory.

### Special Obspy Instructions
Currently PH5 uses a development branch of obspy that will not be official until obspy 1.10.
In order to install this special branch you must do the following:
* Open a terminal
* Run `git clone https://github.com/obspy/obspy.git -b RESPtoInventoryResponse`
* Run `python setup.py install` inside the obspy root directory to install new version of obspy


## Running PH5 Command Line Tools

Once installed, executing command line tools in PH5 couldn't be easier. To run a utility, enter the name of the utility's executable that you wish to run anywhere on the command line.

For example, to run the ph5tostationxml.py utility the user would enter `ph5tostationxml` on the command line.
