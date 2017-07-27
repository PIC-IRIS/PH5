# Contributing to PH5
First, thank you for considering contributing to PH5. Community development from people like you help make PH5 a great data format and software suite.

The goal of this document is to give an overview and basic guidelines for contributing to PH5. By following the guidelines below you help the developers and fellow community members quickly and efficiently address issues you may foind or review code you would like to contribute.

## Getting Started
* Create Github account if you do not already have one
* Install [git](https://git-scm.com/downloads)
* Clone and install a development version of PH5 using `python setup.py develop`

## Submitting a Bug Report or Issue
If you finda bug or have issues using PH5 please first look through the issues tab in github to see if the problem you are encountering is already there. If it is you may find a work around has already been found or someone is currently contributing a fix. Or you may be able to contribute to the discussion of the issue to help resolve it. 

If there is no current issue for your particular bug or issue please creat a new issue. Make your title short but descriptive and in the description go into as much detail as you can. This will help the community and developers quickly address your issue. If you have already started workign on a fix for the issue we thank you! Please still submit an issue and then follow the guideliens below for c reating a pull request for you code contribution.

## Submitting a Pull Request

Pull requests help keep code contributions organized and allow for efficient discussion and review of your contributions. Follow the guidelines below.

If your pull request is related to a current issue or one you have just submitted please make not of this in the issue.

1. CLone and install a development version of PH5 from the `master` branch
2. Create a new branch based on `master`
3. Add your change to this branch. If you are creating new files please make sure you follow pep8 conventions.
4. When editing current files please make sure you update the `PROG_VERSION` string at teh top fo the file with the current year and day of the year (eg: 2017.207)
5. Create a unit test for your contribution and make sure it passes.
6. Push your branch and the submit a pull request from github. Again make sure your base brach is `master`
7. Wait for developer and community review. WE may suggest changes or improvements to your code. Note that this may be an interative process and discussion will take place in the pull request.
8. Once your changes are accepted they wil be scheduled to be added to a future release of PH5 or an incremental release in the case of a bug fix.

We ask that you keep file sizes as small as possible, especially when creating tests. Large files create issues in git.

Please note that by submitting a pull request this implies that you accept that your code will be licensed under the MIT license.

### Thank you again for contributing and once your contributions are accepted you will be added to the contributers list.



