"""
leverages obspy to read in streams/traces
and convert them to PH5

Derick Hess
"""
import logging
import argparse
import os
import sys
import re
from ph5 import LOGGING_FORMAT
from ph5.utilities import initialize_ph5
from ph5.core import experiment, timedoy
from obspy.io.mseed.core import _is_mseed
from obspy.io.mseed.util import get_flags
from obspy import read as reader
from obspy import UTCDateTime, Stream, Trace
from numpy import array

PROG_VERSION = '2024.227'
LOGGER = logging.getLogger(__name__)
DEPRECATION_WARNING = (
    'mstoph5 is no longer supported by the PH5 software. '
    'Please use different functions to format data as PH5.\n\n'
    'To force running the command anyway, please use flag --force\n\n')


class ObspytoPH5Error(Exception):
    """
    Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class ObspytoPH5(object):

    def __init__(self, ph5_object,
                 ph5_path,
                 num_mini=None,
                 first_mini=None):
        """
        :type class: ph5.core.experiment
        :param ph5_object:
        """
        self.ph5 = ph5_object
        self.ph5_path = ph5_path
        self.num_mini = num_mini
        self.first_mini = first_mini
        self.mini_size_max = 26843545600
        self.verbose = False
        self.array_names = self.ph5.ph5_g_sorts.names()
        self.arrays = list()
        for name in self.array_names:
            array_, blah = self.ph5.ph5_g_sorts.read_arrays(name)
            for entry in array_:
                self.arrays.append(entry)
        self.time_t = list()

    def openmini(self, mini_num):
        """
        Open PH5 file, miniPH5_xxxxx.ph5
        :type: str
        :param mini_num: name of mini file to open
        :return class: ph5.core.experiment, str: name
        """

        mini_num = str(mini_num).zfill(5)
        filename = "miniPH5_{0}.ph5".format(mini_num)
        exrec = experiment.ExperimentGroup(
            nickname=filename,
            currentpath=self.ph5_path)
        exrec.ph5open(True)
        exrec.initgroup()
        return exrec, filename

    def get_minis(self, dir):
        """
        takes a directory and returns a list of all mini files
        in the current directory

        :type str
        :param dir
        :return: list of mini files
        """
        miniPH5RE = re.compile(r".*miniPH5_(\d+)\.ph5")
        minis = list()
        for entry in os.listdir(dir):
            # Create full path
            fullPath = os.path.join(dir, entry)
            if miniPH5RE.match(entry):
                minis.append(fullPath)
        return minis

    def get_size_mini(self, mini_num):
        """
        :param mini_num: str
        :return: size of mini file in bytes
        """
        mini_num = str(mini_num).zfill(5)
        filename = "miniPH5_{0}.ph5".format(mini_num)
        return os.path.getsize(filename)

    def get_das_station_map(self):
        """
        Checks if array tables exist
        returns None
        otherwise returns a list of dictionaries
        containing das serial numbers and stations
        :return: list
        """
        array_names = self.ph5.ph5_g_sorts.namesArray_t()
        if not array_names:
            return None
        tmp = list()
        # use tables where to search array tables and find matches
        for _array in array_names:
            tbl = self.ph5.ph5.get_node('/Experiment_g/Sorts_g/{0}'.format(
                _array))
            data = tbl.read()
            for row in data:
                tmp.append({'serial': row[4][0], 'station': row[13]})
        das_station_map = list()
        for i in tmp:
            if i not in das_station_map:
                das_station_map.append(i)
        tbl = None

        return das_station_map

    def mini_map(self, existing_minis):
        """
        :type list
        :param existing_minis: A list of mini_files with path
        :return:  list of tuples containing
        what mini file contains what serial #s
        """
        mini_map = list()
        for mini in existing_minis:
            mini_num = int(mini.split('.')[-2].split('_')[-1])
            exrec = experiment.ExperimentGroup(nickname=mini)
            exrec.ph5open(True)
            exrec.initgroup()
            all_das = exrec.ph5_g_receivers.alldas_g()
            das_list = list()
            for g in all_das:
                name = g.split('_')[-1]
                das_list.append(name)
            mini_map.append((mini_num, das_list))
            exrec.ph5close()
        return mini_map

    def toph5(self, file_tuple):
        """
        Takes a tuple (file_name or obspy stream, type)
        and loads it into ph5_object
        :type tuple
        :param file_tuple containing
        file_handle or obspy stream and file type as str
        :return:
        """
        index_t = list()
        time_corrected = False
        correction = False
        current_mini = None
        in_type = None
        das_station_map = self.get_das_station_map()
        existing_minis = self.get_minis(self.ph5_path)

        if not das_station_map:
            err = "Array metadata must exist before loading data"
            LOGGER.error(err)
            return "stop", index_t

        # gets mapping of whats dases each minifile contains
        minis = self.mini_map(existing_minis)

        # check if we are opening a file or have an obspy stream
        if isinstance(file_tuple[0], str):
            st = reader(file_tuple[0], format=file_tuple[1])
            in_type = "file"
            if file_tuple[1] == 'MSEED':
                try:
                    flags = get_flags(file_tuple[0])
                    if flags['activity_flags_counts'][
                             'time_correction_applied'] > 0:
                        LOGGER.info("Timing correction has been applied")
                        time_corrected = True
                    if flags["timing_correction"] != 0.0:
                        LOGGER.info('Timing Correction found')
                        correction = True

                except BaseException:
                    pass
        # is this an obspy stream?
        elif isinstance(file_tuple[0], Stream):
            st = file_tuple[0]
            in_type = 'stream'
        # is this an obspy trace?
        elif isinstance(file_tuple[0], Trace):
            st = Stream(traces=[file_tuple[0]])
            in_type = 'trace'

        # Loop through data and load it in to PH5
        LOGGER.info('Processing {0} traces in stream for {1}'.format(
            len(st), file_tuple[0]))
        count = 1
        for trace in st:
            if self.verbose:
                LOGGER.info('Processing trace {0} in {1}'.format(
                    trace.stats.channel, trace.stats.station))
            if not trace.stats.channel == 'LOG':
                if not trace.data.any():
                    LOGGER.info("No data for trace {0}...skipping".format(
                        trace.stats.channel))
                    continue
            if not existing_minis:
                current_mini = self.first_mini
            else:
                current_mini = None
                for mini in minis:
                    for entry in das_station_map:
                        if (entry['serial'] in mini[1] and
                                entry['station'] == trace.stats.station):
                            current_mini = mini[0]
                    if not current_mini:
                        largest = 0
                        for x in minis:
                            if x[0] >= largest:
                                largest = x[0]
                        if (self.get_size_mini(largest) <
                                self.mini_size_max):
                            current_mini = largest
                        else:
                            current_mini = largest + 1
            # iterate through das_station_map
            for entry in das_station_map:
                time_t = {}
                das = {}
                index_t_entry = {}
                # only load data if it matches
                if trace.stats.station == entry['station']:

                    # open mini file
                    mini_handle, mini_name = self.openmini(current_mini)
                    # get node reference or create new node
                    d = mini_handle.ph5_g_receivers.getdas_g(entry['serial'])
                    if not d:
                        d, t, r, ti = mini_handle.ph5_g_receivers.newdas(
                            entry['serial'])

                    # start populating das table and data arrays
                    das['time/ascii_s'] = trace.stats.starttime
                    index_t_entry['start_time/ascii_s'] = (
                        trace.stats.starttime.isoformat())
                    time = timedoy.fdsn2epoch(
                        trace.stats.starttime.isoformat(), fepoch=True)
                    microsecond = (time % 1) * 1000000
                    das['time/epoch_l'] = (int(time))
                    das['time/micro_seconds_i'] = microsecond
                    das['time/type_s'] = 'BOTH'
                    index_t_entry['start_time/epoch_l'] = (int(time))
                    index_t_entry['start_time/micro_seconds_i'] = (
                        microsecond)
                    index_t_entry['start_time/type_s'] = 'BOTH'
                    time = timedoy.fdsn2epoch(
                        trace.stats.endtime.isoformat(), fepoch=True)
                    microsecond = (time % 1) * 1000000
                    index_t_entry['end_time/ascii_s'] = (
                        trace.stats.endtime.isoformat())
                    index_t_entry['end_time/epoch_l'] = (int(time))
                    index_t_entry['end_time/micro_seconds_i'] = (
                        microsecond)
                    index_t_entry['end_time/type_s'] = 'BOTH'
                    now = UTCDateTime.now()
                    index_t_entry['time_stamp/ascii_s'] = (
                        now.isoformat())
                    time = timedoy.fdsn2epoch(
                        now.isoformat(), fepoch=True)
                    microsecond = (time % 1) * 1000000
                    index_t_entry['time_stamp/epoch_l'] = (int(time))
                    index_t_entry['time_stamp/micro_seconds_i'] = (
                        int(microsecond))
                    index_t_entry['time_stamp/type_s'] = 'BOTH'

                    if correction or time_corrected:
                        time_t['das/serial_number_s'] = entry['serial']

                        if in_type == 'file':
                            time_t['description_s'] = file_tuple[0]
                        else:
                            time_t['description_s'] = (
                                    str(trace.stats.station) +
                                    str(trace.stats.channel))
                        # SEED time correction
                        # units are 0.0001 seconds per unit
                        time_t['offset_d'] = \
                            flags["timing_correction"] * 0.0001
                        time_t['start_time/epoch_l'] =\
                            index_t_entry['start_time/epoch_l']
                        time_t['start_time/micro_seconds_i'] =\
                            index_t_entry['start_time/micro_seconds_i']
                        time_t['end_time/epoch_l'] =\
                            index_t_entry['end_time/epoch_l']
                        time_t['end_time/micro_seconds_i'] =\
                            index_t_entry['end_time/micro_seconds_i']
                        length = trace.stats.npts * trace.stats.delta
                        if length != 0:
                            time_t['slope_d'] = time_t['offset_d'] / length
                        else:
                            time_t['slope_d'] = 0

                    if time_corrected:
                        time_t['corrected_i'] = 1

                    if time_t:
                        self.time_t.append(time_t)

                    if (trace.stats.sampling_rate >= 1 or
                            trace.stats.sampling_rate == 0):
                        das['sample_rate_i'] = trace.stats.sampling_rate
                        das['sample_rate_multiplier_i'] = 1
                    else:
                        das['sample_rate_i'] = 0
                        das['sample_rate_multiplier_i'] = (
                                1 /
                                trace.stats.sampling_rate)
                    channel_list = list(trace.stats.channel)
                    if channel_list[2] in ({'3', 'Z', 'z'}):
                        das['channel_number_i'] = 3
                    elif channel_list[2] in (
                            {'2', 'E', 'e'}):
                        das['channel_number_i'] = 2
                    elif channel_list[2] in (
                            {'1', 'N', 'n'}):
                        das['channel_number_i'] = 1
                    elif channel_list[2].isdigit():
                        das['channel_number_i'] = channel_list[2]
                    elif trace.stats.channel == 'LOG':
                        das['channel_number_i'] = -2
                        das['sample_rate_i'] = 0
                        das['sample_rate_multiplier_i'] = 1
                    else:
                        das['channel_number_i'] = -5
                    if in_type == 'file':
                        das['raw_file_name_s'] = file_tuple[0]
                    else:
                        das['raw_file_name_s'] = 'obspy_stream'
                    if trace.stats.channel == 'LOG':
                        das['sample_count_i'] = 0
                    else:
                        das['sample_count_i'] = trace.stats.npts

                    # figure out receiver and response n_i
                    for array_entry in self.arrays:
                        if (array_entry['sample_rate_i'] ==
                                trace.stats.sampling_rate and
                                array_entry['channel_number_i'] ==
                                das['channel_number_i'] and
                                array_entry['id_s'] == trace.stats.station):
                            das['receiver_table_n_i'] =\
                                array_entry['receiver_table_n_i']
                            das['response_table_n_i'] =\
                                array_entry['response_table_n_i']

                    # Make sure we aren't overwriting a data array
                    while True:
                        next_ = str(count).zfill(5)
                        das['array_name_data_a'] = "Data_a_{0}".format(
                            next_)
                        node = mini_handle.ph5_g_receivers.find_trace_ref(
                            das['array_name_data_a'])
                        if not node:
                            break
                        count = count + 1
                        continue

                    mini_handle.ph5_g_receivers.setcurrent(d)
                    data = array(trace.data)
                    if trace.stats.channel == 'LOG':
                        mini_handle.ph5_g_receivers.newarray(
                            das['array_name_data_a'], data, dtype='|S1',
                            description=None)
                    else:
                        data_type = data[0].__class__.__name__
                        mini_handle.ph5_g_receivers.newarray(
                            das['array_name_data_a'], data, dtype=data_type,
                            description=None)
                    mini_handle.ph5_g_receivers.populateDas_t(das)

                    index_t_entry['external_file_name_s'] = "./{}".format(
                        mini_name)
                    das_path = "/Experiment_g/Receivers_g/" \
                               "Das_g_{0}".format(entry['serial'])
                    index_t_entry['hdf5_path_s'] = das_path
                    index_t_entry['serial_number_s'] = entry['serial']

                    index_t.append(index_t_entry)
                    # Don't forget to close minifile
                    mini_handle.ph5close()
        LOGGER.info('Finished processing {0}'.format(file_tuple[0]))

        # last thing is to return the index table so far.
        # index_t will be populated in main() after all
        # files are loaded
        return "done", index_t

    def update_external_references(self, index_t):
        """
        looks through index_t and updates master.ph5
        with external references to das group in mini files
        :type list
        :param index_t:
        :return:
        """
        n = 0
        LOGGER.info("updating external references")
        for i in index_t:
            external_file = i['external_file_name_s'][2:]
            external_path = i['hdf5_path_s']
            target = external_file + ':' + external_path
            external_group = external_path.split('/')[3]

            try:
                group_node = self.ph5.ph5.get_node(external_path)
                group_node.remove()

            except Exception as e:
                pass

            #   Re-create node
            try:
                self.ph5.ph5.create_external_link(
                    '/Experiment_g/Receivers_g', external_group, target)
                n += 1
            except Exception as e:
                # pass
                LOGGER.error(e.message)

        return


def getListOfFiles(dirName):
    # create a list of file and sub directories
    # names in the given directory
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles


def get_args(args):
    """
    :return: class: argparse
    """
    parser = argparse.ArgumentParser(
            description='Takes data files and converts to PH5',
            usage=('Version: {0} mstoph5 --nickname="Master_PH5_file" '
                   '[options]\n'
                   'IMPORTANT: {1}').format(PROG_VERSION, DEPRECATION_WARNING),
            epilog=("Notice: Data of a Das can't be stored in more than one "
                    "mini file.")
            )
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5", required=True)

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument(
        "-r", "--raw", dest="rawfile",
        default=None,
        help="Minissed file",
        metavar="miniseed_file")

    file_group.add_argument(
        "-f", "--file", dest="infile",
        default=None,
        help="File containing list of miniseed file names with full path.",
        metavar="file_list_file")

    parser.add_argument(
        "-d", "--dir", dest="indir",
        default=None,
        help="Directory to traverse looking for data",
        metavar="directory")

    parser.add_argument(
        "-M", "--num_mini", dest="num_mini",
        help="Create a given number of miniPH5  files. Ex: -M 38",
        metavar="num_mini", type=int, default=None)

    parser.add_argument(
        "-S", "--first_mini", dest="first_mini",
        help=("The index of the first miniPH5_xxxxx.ph5 "
              "file of all. Ex: -S 5"),
        metavar="first_mini", type=int, default=1)

    parser.add_argument(
        "-V", "--verbose", dest="verbose",
        help="Verbose logging ",
        action='store_true')

    parser.add_argument(
        "--force", dest="force_run",
        help="Force to run the command.",
        action="store_true", default=False)

    return parser.parse_args(args)


def main():
    args = get_args(sys.argv[1:])
    if not args.force_run:
        LOGGER.warning(DEPRECATION_WARNING)
        sys.exit()

    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    PATH = os.path.dirname(args.ph5path) or '.'
    # Debugging
    os.chdir(PATH)
    # Write log to file
    ch = logging.FileHandler(os.path.join(".", "datatoph5.log"))
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)

    if not os.path.exists(ph5file):
        LOGGER.warning("{0} not found. Creating...".format(ph5file))
        # Create ph5 file
        ex = experiment.ExperimentGroup(nickname=ph5file)
        ex.ph5open(True)  # Open ph5 file for editing
        ex.initgroup()
        # Update /Experiment_g/Receivers_g/Receiver_t
        default_receiver_t = initialize_ph5.create_default_receiver_t()
        initialize_ph5.set_receiver_t(default_receiver_t)
        LOGGER.info("Removing temporary {0} kef file."
                    .format(default_receiver_t))
        os.remove(default_receiver_t)
        ex.ph5close()
        LOGGER.info("Done... Created new PH5 file {0}."
                    .format(ph5file))
    # Produce list of valid files from file, list, and dirs
    valid_files = list()
    if args.rawfile:
        if _is_mseed(args.rawfile):
            LOGGER.info("{0} is a valid miniSEED file. "
                        "Adding to process list.".format(args.rawfile))
            valid_files.append((args.rawfile, 'MSEED'))
        else:
            LOGGER.info("{0} is a  NOT valid miniSEED file.".format(
                args.rawfile))

    try:
        if _is_mseed(args.infile):
            LOGGER.error("The given list file is a miniseed file. You have "
                         "been confused between two option -r and -f.")
            sys.exit()
    except TypeError:
        pass

    if args.infile:
        LOGGER.info("Checking list...")
        with open(args.infile) as f:
            content = f.readlines()
        for line in content:
            if os.path.isfile(line.rstrip()):
                if _is_mseed(line.rstrip()):
                    LOGGER.info("{0} is a valid miniSEED file. "
                                "Adding to"
                                "process list.".format(line.rstrip()))
                    valid_files.append((line.rstrip(), 'MSEED'))
                else:
                    LOGGER.info("{0} is NOT a valid miniSEED "
                                "file.".format(line.rstrip()))
            else:
                LOGGER.info("{0} does not exist".format(line.rstrip()))

    if args.indir:
        LOGGER.info("Scanning directory {0} and sub directories...".format(
            args.indir))
        found_files = getListOfFiles(args.indir)
        found_files.sort()
        for f in found_files:
            if _is_mseed(f):
                LOGGER.info("{0} is a valid miniSEED file. "
                            "Adding to process list.".format(f))
                valid_files.append((f, 'MSEED'))
            else:
                LOGGER.info("{0} is NOT a valid miniSEED file.".format(f))

    # take list of valid files and load them into PH5
    ph5_object = experiment.ExperimentGroup(nickname=args.nickname,
                                            currentpath=args.ph5path)
    ph5_object.ph5open(True)
    ph5_object.initgroup()
    obs = ObspytoPH5(ph5_object, args.ph5path,
                     args.num_mini, args.first_mini)
    if args.verbose:
        obs.verbose = True
    obs.get_minis(args.ph5path)
    if args.num_mini:
        total = 0
        for entry in valid_files:
            total = total + os.path.getsize(entry[0])
        obs.mini_size_max = (total*.60)/args.num_mini
    index_t_full = list()

    for entry in valid_files:
        message, index_t = obs.toph5(entry)
        for e in index_t:
            index_t_full.append(e)
        if message == "stop":
            LOGGER.error("Stopping program...")
            break
    if len(obs.time_t) > 0:
        LOGGER.info('Populating Time table')
        for entry in obs.time_t:
            ph5_object.ph5_g_receivers.populateTime_t_(entry)
    LOGGER.info("Populating Index table")
    for entry in index_t_full:
        ph5_object.ph5_g_receivers.populateIndex_t(entry)

    obs.update_external_references(index_t_full)
    ph5_object.ph5close()


if __name__ == '__main__':
    main()
