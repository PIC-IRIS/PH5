#!/usr/bin/env pnpython3

import argparse
import logging
import os
from ph5.core import kef, experiment

PROG_VERSION = '2018.270'
LOGGER = logging.getLogger(__name__)


def get_args():
    ''' Parse input args
           -n   output file
           -E   experiment_t kef file (optional)
           -C   receiver_t kef file (optional)
    '''
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)
    parser.usage = ("initialize_ph5 --n output_file [options]")
    parser.description = ("Program to initialize PH5 file at start of "
                          "experiment.\n\nVersion: {0}"
                          .format(experiment.PROG_VERSION))
    parser.add_argument("-n", "--nickname", dest="outfile",
                        help=("Experiment nickname of ph5 file to create. "
                              "(e.g. master.ph5)"),
                        metavar="output_ph5_file",
                        required=True)
    parser.add_argument("-E", "--Experiment_t", dest="experiment_t",
                        help="/Experiment_g/Experiment_t kef file to load.",
                        required=False)
    parser.add_argument("-C", "--Receiver_t", dest="receiver_t",
                        help=("Alternate "
                              "/Experiment_g/Receivers_g/Receiver_t kef "
                              "file to load."),
                        required=False)
    try:
        args = parser.parse_args()
    except BaseException:
        raise ValueError("Missing required argument.")
    else:
        if args.receiver_t:
            args.receiver_t = os.path.abspath(args.receiver_t)
    return args


def create_default_receiver_t():
    """
    Creates /Experiment_g/Receivers_g/Receiver_t table with default
    values.
    """
    receiver_t_default = "receiver_t.tmp"
    receiver_t_default_string = str("""
    /Experiment_g/Receivers_g/Receiver_t
            orientation/azimuth/value_f = 0.0
            orientation/azimuth/units_s = degrees
            orientation/dip/value_f = 90.0
            orientation/dip/units_s = degrees
            orientation/description_s = Z
    /Experiment_g/Receivers_g/Receiver_t
            orientation/azimuth/value_f = 0.0
            orientation/azimuth/units_s = degrees
            orientation/dip/value_f = 0.0
            orientation/dip/units_s = degrees
            orientation/description_s = N
    /Experiment_g/Receivers_g/Receiver_t
            orientation/azimuth/value_f = 90.0
            orientation/azimuth/units_s = degrees
            orientation/dip/value_f = 0.0
            orientation/dip/units_s = degrees
            orientation/description_s = E
    /Experiment_g/Receivers_g/Receiver_t
            orientation/azimuth/value_f = 0.0
            orientation/azimuth/units_s = degrees
            orientation/dip/value_f = -90.0
            orientation/dip/units_s = degrees
            orientation/description_s = Z
            """)
    LOGGER.info("Creating temporary {0} kef file "
                "using default values."
                .format(receiver_t_default))
    kef_file = open(receiver_t_default, "w")
    kef_file.write(receiver_t_default_string)
    kef_file.close()
    return receiver_t_default


def set_experiment_t(experiment_t):
    if experiment_t and os.path.exists(experiment_t):
        LOGGER.info("Loading /Experiment_g/Experiment_t using {0}."
                    .format(experiment_t))
        k = kef.Kef(experiment_t)
        k.open()
        k.read()
        k.batch_update()
        k.close()
    else:
        LOGGER.warning("Experiment_g/Experiment_t not set! "
                       "Use --kef option to supply a Experiment_t kef file.")


def set_receiver_t(receiver_t):
    if os.path.exists(receiver_t):
        LOGGER.info("Loading Experiment_g/Receivers_g/Receiver_t using {0}."
                    .format(receiver_t))
        k = kef.Kef(receiver_t)
        k.open()
        k.read()
        k.batch_update()
        k.close()
    else:
        LOGGER.warning("{0} file not found.".format(receiver_t))


def main():
    try:
        args = get_args()
    except ValueError:
        pass  # Error parsing arguments
    else:
        # Create ph5 file
        ex = experiment.ExperimentGroup(nickname=args.outfile)
        ex.ph5open(True)  # Open ph5 file for editing
        ex.initgroup()
        # Update /Experiment_g/Experiment_t
        set_experiment_t(args.experiment_t)

        # Update /Experiment_g/Receivers_g/Receiver_t
        if args.receiver_t:
            set_receiver_t(args.receiver_t)
        else:
            LOGGER.warning("Experiment_g/Receivers_g/Receiver_t set using "
                           "default values. Use --receiver_t option to supply "
                           "a Receiver_t kef file.")
            default_receiver_t = create_default_receiver_t()
            set_receiver_t(default_receiver_t)
            LOGGER.info("Removing temporary {0} kef file."
                        .format(default_receiver_t))
            os.remove(default_receiver_t)

        # Close PH5 file
        ex.ph5close()
        LOGGER.info("Done... Created new PH5 file {0}."
                    .format(args.outfile))


if __name__ == "__main__":
    main()
