from ph5.core import experiment


def initialize_ex(nickname, path, editmode=False):
    """
    many test files used this function. However many functional files use this
    function as well. Wonder if this file should be here.
    """
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex
