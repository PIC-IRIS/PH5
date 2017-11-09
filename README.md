# PH5 
[![Build Status](https://travis-ci.org/PIC-IRIS/PH5.svg?branch=master)](https://travis-ci.org/PIC-IRIS/PH5) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) [![DOI](https://zenodo.org/badge/66882151.svg)](https://zenodo.org/badge/latestdoi/66882151)


A library of command line utilities and APIs for building and interacting with PH5 datasets. 

**See the [PH5 Wiki](https://github.com/PIC-IRIS/PH5/wiki) for information about the strucuture and use of PH5**

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
* Install [Git](https://git-scm.com/downloads) if you do not have it
* Clone the PH5 project from GitHub to your local machine by running `git clone https://github.com/PIC-IRIS/PH5.git` or downloading the zip file from the main github page .
* Add the conda-forge channel to your Anaconda configuration by running `conda config --add channels conda-forge`
* Create a new Anaconda Virtual Environment for ph5 by running `conda create -q --name=ph5 python=2.7`
* Install PH5 dependencies into the environment from the PH5 directory created by git by running `conda env update --name=ph5 -f=/path/to/ph5/environment.yml`
* Source the newly created ph5 environment by running `source activate ph5` (note that your are required to use bash shell for this to work)
* Install the PH5 python package by running `python setup.py install` in the cloned PH5 project root directory.

## Running PH5 Command Line Tools

Once installed, executing command line tools in PH5 couldn't be easier. To run a utility, enter the name of the utility's executable that you wish to run anywhere on the command line.

Lists of command line utilities may be found at the links below:
* [Data/Metadata Ingestion](https://github.com/PIC-IRIS/PH5/wiki/Data-and-Metadata-Ingestion)
* [Data/Metadata QC](https://github.com/PIC-IRIS/PH5/wiki/Data-and-Metadata-QC)
* [Editing and Manipulation](https://github.com/PIC-IRIS/PH5/wiki/PH5-Editing-and-Manipulation)
* [Data Extraction](https://github.com/PIC-IRIS/PH5/wiki/Data-Extraction)
