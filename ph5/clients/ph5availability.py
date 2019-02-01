# Derick Hess, Feb 2019

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
from ph5.core import ph5api

PROG_VERSION = '2019.32'
LOGGER = logging.getLogger(__name__)


class PH5AvailabilityError(Exception):
    """Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class PH5Availability(object):

    def __init__(self, ph5API_object):
        self.ph5 = ph5API_object
        return


def get_args():

    import argparse
    parser = argparse.ArgumentParser(
        description='Get data availability form PH5',
        usage='Version: {0} ph5availability '
              '--nickname="Master_PH5_file" [options]'.format(PROG_VERSION))
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    the_args = parser.parse_args()
    return the_args


def main():
    args = get_args()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)
    try:
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)
        PH5Availability(ph5API_object)

    except ph5api.APIError as err:
        LOGGER.error(err)
    except PH5AvailabilityError as err:
        LOGGER.error(err)
    except Exception as e:
        LOGGER.error(e)


if __name__ == '__main__':
    main()
