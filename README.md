# PH5 [![Build Status](https://travis-ci.org/PIC-IRIS/PH5.svg?branch=master)](https://travis-ci.org/PIC-IRIS/PH5)
A library of command line utilities and apis for interacting with a PH5 dataset.

# Detailed Installation Instructions

The easiest way to install PH5 is to use the Anaconda distribution of python. These instructions
only cover installation of PH5 dependencies using Anaconda. This is because PH5 (and many python tools) require packages (aka modules) that have C dependencies.

## Anaconda is not a requirement
Anaconda is not an absolute requirement to get PH5 to work. As long as you can get the necessary python dependencies installed, PH5 will work. If you want to install Anaconda, follow the Windows, Macs, and Linux instructions below.

### Windows
The Anaconda installer should be able to be double-clicked and installed. Use all of the defaults for installation except make sure to check Make Anaconda the default Python.

### Macs
After downloading the installer, double click the .pkg file and follow the instructions on the screen. Use all of the defaults for installation.

### Linux
After downloading the installer execute the associated shell script. For example, if the file downloaded were named Anaconda3-4.1.1-Linux-x86_64.sh you would enter bash Anaconda3-4.1.1-Linux-x86_64.sh in the directory where you downloaded the file.

## Installing PH5

### Installing from source
* Open a terminal and clone the PH5 project
* Clone the PH5 project from GitHub to your local machine.
* Add the conda-forge channel to your Anaconda configuration by running `conda config --add channels conda-forge`
* Install PH5 Dependencies by running `conda env update -f=/path/to/ph5/environment.yml`. PH5 dependencies will be 
created in a new Anaconda Virtual Environment called _ph5_
* Source the newly created ph5 environment by running `source activate ph5`
* Install the PH5 python package by running `python setup.py install` in the cloned PH5 project root directory.

## Running PH5 Command Line Tools

Once installed, executing command line tools in PH5 couldn't be easier. To run a utility, enter the name of the utility's executable that you wish to run anywhere on the command line.

For example, to run the ph5tostationxml.py utility the user would enter `ph5tostationxml` on the command line.
