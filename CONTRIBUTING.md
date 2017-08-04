# Contributing to PH5
Thank you for considering contributing to PH5. Community development from people like you help make PH5 a great data format and software suite.

The goal of this document is to give an overview and basic guidelines for contributing to PH5.

## Getting Started
* Create a GitHub account if you do not already have one
* Install [Git](https://git-scm.com/downloads)
* Clone and install a development version of PH5 using `python setup.py develop` or `pip install -e .`

## Reporting a Bug or Issue
If you find a bug or have issues using PH5 please first look through the existing [issues](https://github.com/PIC-IRIS/PH5/issues) to see if the problem you are encountering has already been reported. If it is then you may find a work around has already been found or that someone is currently contributing a fix. We welcome you to contribute to the discussion of the issue to help resolve it. 

If there is no current issue for your particular issue please create a new issue. Make your title short but descriptive and in the description go into as much detail as you can. This will help the community and developers quickly address your issue. If you have already started working on a fix for the issue we thank you! Please still submit an issue and then follow the guidelines for submitting a pull request for your code contribution.

## Submitting a Pull Request

To contribute to PH5 you need to submit a new pull request. Pull request allow for efficient discussion and review of your contributions. Please follow the guidelines below.

If your pull request is related to a current issue or one you have just submitted please note this in the issue.

1. Clone and install a development version of PH5 from the `ph5:master` branch.
2. Create a new branch from the `ph5:master` branch.
3. Add your change to this branch. If you are creating new files please follow [PEP8](https://www.python.org/dev/peps/pep-0008/) conventions.
4. When editing existing files please update the `PROG_VERSION` string at the top of the file with the current year and day-of-year (e.g: 2017.207)
5. Create a unit test(s) for your contribution and make sure it passes. If a test module doesn't already exist for the module you are updating, create one in the appropriate test package following the _test\_\<module-name\>_ file-name pattern and then update the PH5/runtests.py script.
6. Push your branch and then submit a pull request. Again make sure your base branch is `ph5:master`.
7. Wait for developer and community review. We may suggest changes or improvements to your code. Note that this may be an interactive process and discussion will take place in the pull request.
8. Once your changes are accepted they will be scheduled to be added to a future release of PH5 or an incremental release in the case of a bug fix.

We ask that you keep file sizes as small as possible, especially when creating tests. Large files create issues in Git.

Please note that by submitting a pull request this implies that you accept that your code will be licensed under the MIT license.

### Thank you again for contributing. Once your contributions are accepted you will be added to the contributers list.



