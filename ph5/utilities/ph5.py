#!/usr/bin/env pnpython4
#
# Produce SEG-Y in shot (event) order from PH5 file using API
#
# Steve Azevedo, August 2016
#

import argparse

PROG_VERSION = "2019.37 Developmental"


def main():
    parser = argparse.ArgumentParser(
        description="Get Usage Info for PH5 Subprograms")
    parser.add_argument("n", type=str, nargs="?",
                        default='', help="PH5 subprogram name")

    string = ""

    try:
        args = parser.parse_args()
        # print "arg.ns:", args.n, ", len = ", len(args.n)

        try:
            if len(args.n) == 0:  # no argument provided by user
                showlist()
        except TypeError:
                showlist()

        args.n = args.n.lower()

        nlen = len(args.n)  # asterisked display of program name
        if nlen > 0:
            targlen = 60
            nstar = (targlen-nlen)/2 - 1
            print "*" * targlen
            nstr = "*" * nstar + " " + args.n + " " + "*" * nstar
            lnstr = len(nstr)
            if lnstr < targlen:
                nstr = nstr + "*" * (targlen - lnstr)
            elif lnstr > targlen:
                nstr = nstr[0:targlen]
            print nstr
            print "*" * targlen

        if args.n == "ph5view":  # GUI
            string = """ph5view is a GUI program for plotting responses,
saving files to SEGY, etc.
It has three main panels: Control, Main, and Support.
Control Panel: the panel with the menu and three tabs
(Control, Shot Gather, Receiver Gather).
Main Window: the main panel for plotting.
Support Window: the panel to show small portion of the
plot (the idea is to reduce the amount of trace need
to be analyzed).
Consult the Help Utility in ph5view to learn more."""
        elif args.n == "noven":
            string = """noven is the Graphic User Interface (GUI) that
allows users to load the CSV format metadata files that they
created for the receiver and shot arrays, specify the columns,
and then save the array tables as PH5 compatible kef files
that can be loaded into the master.ph5 file.
The main noven menu (under File) has several useful
options: Open (CSV file), Check Input, Map Locations,
and Save As...
Consult the Help Utility in noven to learn more."""
        elif args.n == "pforma":
            string = """Data is loaded into PH5 using a
GUI program called pforma.
pforma takes all of the raw data files referenced in the
list you created earlier and divides them up to multi-
thread the loading process to make it faster.
pforma will use all available cores on your system.
Currently, this is not configurable.
pforma creates multiple subdirectories in the PH5
directory. After loading all of the data using pforma,
you will merge the resulting subdirectories into a complete
PH5. After selection of the file with the list of raw
files, and the processing directory, the user specifies
the UTM Zone and the number of SEG-D traces to combine,
and clicks Run.
Once the run is finished, the user can click Merge to
merge the resulting subdirectories into a complete PH5.
If you have node data from multiple UTM zones, you will
need to run pforma for the data for each UTM zone
separately in order to correctly map the node locations
into the PH5 archive."""
        elif args.n == "kefedit":
            string = """kefedit is a GUI interface for opening, editing,
and saving .kef and .ph5 files. It has a detailed help section which describes.
the available functions and options.

Open Kef File: to open all tables in a Kef file for editing.
Each table is placed in a tab.

Open PH5 File: to open (a) table(s) in a PH5 File for editing.
Each table is placed in a tab.

Tables can be saved in .kef, .phf or .csv formats.

"""
        elif args.n == "experiment_t_gen":
            string = """The experiment_t_gen GUI is run in the
metadata directory, to build the experiment
summary kitchen-exchange format (kef) file.
Required fields include nickname, long name, net code,
PIs, institutions, coordinates for the bounding box,
summary paragraph, and experiment ID (assembled ID)."""
        elif args.n == "125atoph5":  # console
            string = """The 125atoph5 console application
allows the user to add Texan raw data to the PH5 file.
The 'trd_list' should list the absolute or relative
path and file names for Texan data files.
Use the 'M' option, specifying 1/6th the data volume
to be loaded, in integer GB (you can use du -sh ../RAW
to estimate data volume).
The 'M' option causes the data to be uploaded into a
number of 'data-only' ph5 files (called 'mini' files)
linked to the master ph5 file, optimizing subsequent
data processing and extraction.
Example:
125atoph5 –f trd_list –n master.ph5 –M 17 >& 125a2ph5.out

optional arguments:
 -h, --help            show this help message and exit
 -r raw_file, --raw raw_file
                       RT-125(a) texan raw file
 -f file_list_file, --file file_list_file
                       File containing list of RT-125(a) raw file names.
 -o, --overide         Overide file name checks.
 -n output_file_prefix, --nickname output_file_prefix
                       The ph5 file prefix (experiment nick name).
 -M num_mini, --num_mini num_mini
                       Create given number of miniPH5_xxxxx.ph5 files.
 -S first_mini, --first_mini first_mini
                       The index of the first miniPH5_xxxxx.ph5 file.
 -s samplerate, --samplerate samplerate
                       Extract only data at given sample rate.
 -w windows_file, --windows_file windows_file
                       File containing list of time windows to process.
Window start time Window length, seconds
                        -----------------   ----
                        YYYY:JJJ:HH:MM:SS   SSSS
 -p                    Do print"""
        elif args.n == "130toph5":  # ?
            string = """The 130toph5 console application
allows the user to add Reftek RT130 raw data to the
PH5 file. The 'file_list' should list the absolute or
relative path and file names for RT130 data files.
Use the 'M' option, specifying 1/2th the data volume to
be loaded, in integer GB (you can use du -sh ../RAW to
estimate data volume).
The 'M' option causes the data to be uploaded into a
number of 'data-only' ph5 files (called 'mini' files)
linked to the master ph5 file, optimizing subsequent
data processing and extraction.
Example:
130atoph5 –f file_list –n master.ph5 –M 17 >& 130toph5.out"""
        elif args.n == "cross_check_event_array_data":
            string = """Cross check Event, Array, and Data.

usage: cross_check_event_array_data [-h]
 --array_json ARRAY_JSON --event_json
  EVENT_JSON --data_json DATA_JSON
  [--offset_secs OFFSET_SECS] [--csv]
  [--epoch]

optional arguments:
  -h, --help            show this help message and exit
--array_json ARRAY_JSON
              As returned by meta-data-gen -r.
--event_json EVENT_JSON
              As returned by meta-data-gen -e.
--data_json DATA_JSON
              As returned by meta-data-gen -d.
--offset_secs OFFSET_SECS
--csv                 Separate output columns with ',' instead of ' '.
--epoch               Times as epoch."""
        elif args.n == "csvtokef":
            string = """Converts a csv generated by keftocsv to a kef file

Usage: keftocsv --file="csvfile" --outfile="keffile"

Optional arguments:
-h, --help            show this help message and exit
-f file, --file file  path to csv file to convert.
-o outfile, --outfile outfile
                       path to kef file to create."""
        elif args.n == "dumpfair":
            string = """dumpfair is a utility for Fairfield Nodes that can be
used to determine how many samples are in each SEG-D file.
The number of samples is in the Trace Header Extension 1
as samples_per_trace.

Typical usage:
dumpfair 1.fcnt | grep samples_per_trace | head -1
use -h, --help option for complete help message."""
        elif args.n == "dumpsac":
            string = """Translate and dump a binary SAC file to stdout.

Typical usage: dumpsac -f sacfile -p

optional arguments:
 -h, --help  show this help message and exit
 -f INFILE
 -p"""
        elif args.n == "dumpsgy":
            string = """Translate and dump a binary SEGY file to stdout.

Typical usage: dumpsgy -f segyfile -t P -e 'big'

optional arguments:
 -h, --help            show this help message and exit
 -f INFILE
 -t {U,P,S,N,I}        Extended trace header style.
   U => USGS Menlo, P => PASSCAL, S => SEG, I => SIOSEIS, N => iNova FireFly
 -p
 -L BYTES_PER_TRACE
 -T TRACES_PER_ENSEMBLE
 -F TRACE_FORMAT       1 = IBM - 4 bytes, 2 = INT - 4 bytes,
3 = INT - 2 bytes, 5 = IEEE - 4 bytes, 8 = INT - 1 byte
 -e ENDIAN             Endianess: 'big' or 'little'. Default = 'big'
 -i                    EBCDIC textural header."""
        elif args.n == "fix_3chan_texan":
            string = """For fixing 3-channel Texan data.
Typical usage: fix_3chan_texan filename.ph5"""
        elif args.n == "fix_num_samples":
            string = """Correct number of samples in time series array
to work around a bug in certain data loggers.
Set sample_count_i in Das_t based on length
of data array. Writes kef file, 1 per DAS.

usage: fix_num_samples --nickname ph5-file-prefix
 [--path path-to-ph5-files]

optional arguments:
 -h, --help            show this help message and exit
 -n ph5_file_prefix, --nickname ph5_file_prefix
                       The ph5 file prefix (experiment nickname).
 -p ph5_path, --path ph5_path
                       Path to ph5 files. Default to current directory.
 -c, --check
 -d"""
        elif args.n == "geo_kef_gen":
            string = """Read locations and calculate offsets from events
to receivers. Produce kef file to populate ph5 file.

Usage: geod2kef --nickname ph5-file-prefix [-p path]

optional arguments:
 -h, --help            show this help message and exit
 -n ph5_file_prefix, --nickname ph5_file_prefix
                       The ph5 file prefix (experiment nickname).
 -p ph5_path, --path ph5_path
                       Path to ph5 files. Defaults to current directory."""
        elif args.n == "graotoph5":
            string = """Load MSEED data into a family of ph5 files.
Can also read using web services.

Usage: grao2ph5 [--help][--raw raw_file |
 --file file_list_file] --nickname output_file_prefix

optional arguments:
 -h, --help            show this help message and exit
 -f file_list_file, --file file_list_file
                       File containing list of:
                       WS:net_code:station:location:channel:
deploy_time:pickup_time:length.
 -n output_file_prefix, --nickname output_file_prefix
                       The ph5 file prefix (experiment nick name).
 -M num_mini, --num_mini num_mini
                       Create a given number of miniPH5_xxxxx.ph5files.
 -S first_mini, --first_mini first_mini
                       The index of the first miniPH5_xxxxx.ph5 file.
 -s samplerate, --samplerate samplerate
                       Extract only data at given sample rate.
 -p                    Do print"""
        elif args.n == "index_offset_t":
            string = """Index offset table in ph5 file to
speed up execution of kernel searches.

usage: index_offset_t --nickname ph5-file-prefix

optional arguments:
 -h, --help  show this help message and exit
 -n ph5_file_prefix, --nickname ph5_file_prefix
      The ph5 file prefix (experiment nickname).
 -p ph5_path, --path ph5_path
      Path to ph5 files. Default to current directory.
 -t offset_table_name, --offset_table offset_table_name
     The name of the offset table. Ex: Offset_t_001_003."""
        elif args.n == "initialize_ph5":
            string = """Program to initialize PH5 file at start of experiment.

usage: initialize_ph5 --n output_file [options]

optional arguments:
  -h, --help  show this help message and exit
  -n output_ph5_file, --nickname output_ph5_file
       Experiment nickname of ph5 file to create.
(e.g. master.ph5).
  -E EXPERIMENT_T, --Experiment_t EXPERIMENT_T
       /Experiment_g/Experiment_t kef file to load.
  -C RECEIVER_T, --Receiver_t RECEIVER_T
      Alternate /Experiment_g/Receivers_g/Receiver_t
kef file to load."""
        elif args.n == "keftocsv":
            string = """Converts a kef file to csv.

usage: keftocsv --file=kef_file --outfile=csvfile

optional arguments:
  -h, --help  show this help message and exit
  -f file, --file file  path to kef file to convert.
  -o outfile, --outfile outfile
           path to csv file to create"""
        elif args.n == "keftokml":
            string = """Converts a kef file to kml format.

usage: keftokml [-h] -k KEFILE -t TITLE

optional arguments:
  -h, --help  show this help message and exit
  -k KEFILE, --kef KEFILE
           The input kef file,Array_t.kef or Event_t.kef.
  -t TITLE, --title TITLE
           Name of the output kml file"""
        elif args.n == "keftoph5":
            string = """Update a ph5 file from a kef file.
usage:  kef2ph5 --kef kef_file --nickname
ph5_file_prefix [--path path]
optional arguments:
 -h, --help  show this help message and exit
  -n OUTFILE, --nickname OUTFILE
            The ph5 file prefix (experiment nickname)
  -k KEFFILE, --kef KEFFILE
           Kitchen Exchange Format file.
  -p PATH, --path PATH  Path to directory where
ph5 files are stored
  -c, --check  Show what will be done but don't do it!"""
        elif args.n == "load_das_t":
            string = br"""Load a batch of Das_t keffiles.

usage: v2019.14: load_das_t options

optional arguments:
  -h, --help   show this help message and exit
  --path PATH  Path to merged PH5 families. Normally in /Sigma
  --re RE      Regular expression for das table kef
               files.Default:\"Das_t_response_n_i_(\w{3,16})\.kef\"
  --onlyload   Only load table, don't clear existing table.
  --onlysave   Save existing table as kef then clear table."""
        elif args.n == "meta_data_gen":
            string = """Write info about receivers, events, or data.

usage: meta_data_gen --nickname=ph5-file-prefix options

optional arguments:
  -h, --help  show this help message and exit
  -E, --experiment      Write info about experiment
to stdout,Experiment_t.json
  -n ph5_file_prefix, --nickname ph5_file_prefix.
            The ph5 file prefix (experiment nickname)
  -p ph5_path, --path ph5_path
        Path to ph5 files.Defaults to current directory
  -r, --receivers       Write info about receivers to
stdout,Array_t_all.json
  -e, --events          Write info about events
to stdout, Event_t.json
  -d, --data            Write info about data to
stdout, Das_t_all.json
  --debug"""
        elif args.n == "nuke_table" or args.n == "delete_table":
            string = """Initialize a table in a ph5 file.
Caution:Deletes contents of table!

usage: delete_table --nickname ph5-file-prefix [options]

optional arguments:
  -h, --help  show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
           The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
           Path to ph5 files. Default to current directory.
  -d
  -N, --no_backup       Do NOT create a kef file backup of the table
  -E, --Experiment_t    Nuke /Experiment_g/Experiment_t
  -S, --Sort_t          Nuke /Experiment_g/Sorts_g/Sort_t
  -O a_e, --Offset_t a_e
            Nuke /Experiment_g/Sort_g/Offset_t_
[arrayID_eventID] to a kef file
  -V n, --Event_t n     Nuke /Experiment_g/Sorts_g/
Event_t_[n]. Use 0 for Event_t
  -A n, --Array_t_ n    Nuke /Experiment_g/Sorts_g/Array_t_[n]
  -R, --Response_t      Nuke /Experiment_g/Responses_g/Response_t
  -P, --Report_t        Nuke /Experiment_g/Reports_g/Report_t
  -C, --Receiver_t      Nuke /Experiment_g/Receivers_g/Receiver_t
  -I, --Index_t         Nuke /Experiment_g/Receivers_g/Index_t
  -M, --M_Index_t       Nuke /Experiment_g/Maps_g/Index_t
  -D das, --Das_t das   Nuke/Experiment_g/Receivers_g/Das_g_[das]/Das_t
  -T, --Time_t          Nuke /Experiment_g/Receivers_g/Time_t"""
        elif args.n == "pformacl":
            string = """Create or open a project and process raw data to
PH5 in parallel.

usage: pforma --project_home=/path/to/project
     --files=list_of_raw_files [options] | --proj

optional arguments:
  -h, --help  show this help message and exit
  -f file_list_file, --files file_list_file
           File containing list of raw file names.
  -p HOME, --project_home HOME
           Path to project directory.
  -n NFAMILIES, --num_families NFAMILIES
       Number of PH5 families to process.
Defaults to number of CPU's + 1 else number of raw files
  -M NUM_MINIS, --num_minis NUM_MINIS
       Number of mini ph5 files per family
  -U UTM      The UTM zone if required for SEG-D conversion
  -T, --TSPF     Coordinates is texas state
plane coordinates (SEG-D)
  -m, --merge    Merge all families to one
royal family in A"""
        elif args.n == "ph5toevt":
            string = """ph5toevt: extract events from ph5 archive.
Version: 2017.312 Developmental

Usage:
ph5toevt --eventnumber=shot --nickname=experiment_nickname
     --length=seconds [--path=ph5_directory_path] [options]
options:
    --array=array, --offset=seconds (float),
    --reduction_velocity=km-per-second (float) --format=['SEGY']

ph5toevt --allevents --nickname=experiment_nickname
    --length=seconds [--path=ph5_directory_path] [options]
    options:
    --array=array, --offset=seconds (float),
        --reduction_velocity=km-per-second (float) --format=['SEGY']

ph5toevt --starttime=yyyy:jjj:hh:mm:ss[:.]sss
    --nickname=experiment_nickname --length=seconds
        [--path=ph5_directory_path] [options]
    options:
    --stoptime=yyyy:jjj:hh:mm:ss[:.]sss,
    --array=array, --reduction_velocity=km-per-second (float)
    --format=['SEGY']

    general options:
    --channel=[1,2,3]
        --sample_rate_keep=sample_rate
    --notimecorrect
        --decimation=[2,4,5,8,10,20]
    --out_dir=output_directory

Generate SEG-Y gathers in shot order...

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Default current directory.
  --channel seed_channel
                        Filter on SEED channel.
  --network seed_network
                        Filter on SEED net code.
  --location seed_location
                        Filter on SEED loc code.
  -c channels, --channels channels
                        List of comma seperated channels to extract.
                        Default = 1,2,3.
  -e event_number, --eventnumber event_number
  --event_list evt_list
                        Comma separated list of event id's to gather from
                        defined or selected events.
  -E, --allevents       Extract all events in event table.
  --shot_line shot_line
                        The shot line number that holds the shots.
  --shot_file shot_file
                        Input an external kef file that contains event
                        information, Event_t.kef.
  -s start_time, --starttime start_time
  -A station_array, --station_array station_array
                        The array number that holds the station(s).
  -l length, --length length
  -O seconds_offset_from_shot,
      --seconds_offset_from_shot seconds_offset_from_shot,
      --offset seconds_offset_from_shot
                        Time in seconds from shot time to start the trace.
  -N, --notimecorrect
  -o out_dir, --out_dir out_dir
  --stream              Write to stdout instead of a file.
  --use_deploy_pickup   Use deploy and pickup times to determine if data
                        exists for a station.
  -S stations_to_gather, --stations stations_to_gather,
      --station_list stations_to_gather
                        Comma separated list of stations to receiver gather.
  -r sample_rate, --sample_rate_keep sample_rate
  -V red_vel, --reduction_velocity red_vel
                        Reduction velocity in km/sec.
  -d decimation, --decimation decimation
  -U, --UTM             Fill SEG-Y headers with UTM instead of lat/lon.
  -x extended_header_style, --extended_header extended_header_style
                        Extended trace header style: 'P' -> PASSCAL, 'S' ->
                        SEG, 'U' -> Menlo USGS, default = U
  --ic
  --break_standard      Force traces to be no longer than 2^15 samples.
  --debug"""
        elif args.n == "ph5toms":
            string = """Return mseed from a PH5 file.
Usage: ph5toms --nickname="Master_PH5_file" [options]

Return mseed from a PH5 file.

optional arguments:
  -h, --help            show this help message and exit
  -n nickname, --nickname nickname
  -p ph5_path, --ph5path ph5_path
  -o out_dir, --out_dir out_dir
  --reqtype REQTYPE
  --channel channel     Comma separated list of SEED channels to extract
  -c component, --component component
                        Comma separated list of channel numbers to extract
  --shotline shotline
  -e eventnumbers, --eventnumbers eventnumbers
  --stream              Stream output to stdout.
  -s start_time, --starttime start_time
                        Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-
                        ddTHH:MM:SS.ss
  -t stop_time, --stoptime stop_time
                        Time formats are YYYY:DOY:HH:MM:SS.ss or YYYY-mm-
                        ddTHH:MM:SS.ss
  -a array, --array array
                        Comma separated list of arrays to extract
  -O offset, --offset offset
                        Offset time in seconds
  -d decimation, --decimation decimation
  --station sta_list    Comma separated list of SEED station id's
  --station_id sta_id_list
                        Comma separated list of PH5 station id's
  -r sample_rate, --sample_rate_keep sample_rate
                        Comma separated list of sample rates to extract
  -l length, --length length
  --notimecorrect
  --use_deploy_pickup   Use deploy/pickup times to determine if data exists.
  -F format, -f format, --format format
                        SAC or MSEED
  --non_standard        Change filename from standard output to
                        [array].[seed_station].[seed_channel].[start_time]
"""
        elif args.n == "ph5torec":
            string = """Generate SEG-Y gathers in receiver order...

Usage: ph5torec -n nickname -p path_to_ph5_files
--stations=stations_list --shot_line --length [options]

optional arguments:
 -h, --help            show this help message and exit
 -n ph5_file_prefix, --nickname ph5_file_prefix
                       The ph5 file prefix (experiment nickname).
 -p ph5_path, --path ph5_path
                       Path to ph5 files. Defaults to current directory.
 --channel seed_channel
                       Filter on SEED channel.
 --network seed_network
                       Filter on SEED net code.
 --location seed_location
                       Filter on SEED loc code.
 -c channels, --channels channels
                       List of comma seperated channels to extract.
Default = 1,2,3.
 -S stations_to_gather, --stations stations_to_gather,
--station_list stations_to_gather
                       Comma separated list of stations to receiver gather.
 --event_list evt_list
                       Comma separated list of event id's to gather from
                       defined or selected events.
 -l length, --length length
 -O seconds_offset_from_shot, --seconds_offset_from_shot
seconds_offset_from_shot, --offset seconds_offset_from_shot
                       Time in seconds from shot time to start the trace.
 -A station_array, --station_array station_array
                       The array number that holds the station(s).
 --shot_line shot_line
                       The shot line number that holds the shots.
 --shot_file shot_file
                       Input an external kef file that contains event
                       information, Event_t.kef.
 -o out_dir, --out_dir out_dir
 --stream              Write to stdout instead of a file.
 -r shot_range, --shot_range shot_range
                       example: --shot_range=1001-11001
 -V red_vel, --reduction_velocity red_vel
 -d decimation, --decimation decimation
 --sort_by_offset
 --use_deploy_pickup   Use deploy and pickup times to determine if data
                       exists for a station.
 -U, --UTM             Fill SEG-Y headers with UTM instead of lat/lon.
 -x extended_header_style, --extended_header extended_header_style
                       Extended trace header style: 'P' -> PASSCAL, 'S' ->
                       SEG, 'U' -> Menlo USGS, default = U
 --ic
 --break_standard      Force traces to be no longer than 2^15 samples.
 -N, --notimecorrect
 --debug"""
        elif args.n == "ph5tostationxml":
            string = """Takes PH5 files and returns StationXML.
usage: ph5tostationxml --nickname=\"Master_PH5_file\" [options]
optional arguments:
 -h, --help            show this help message and exit
 -n nickname, --nickname nickname
 -p ph5path, --ph5path ph5path
                       Comma separated list of paths to ph5 experiments.
 --network network_list
                      Comma separated list of networks. Wildcards accepted
 --reportnum reportnum_list
                       Comma separated list of report numbers. Wildcards
                       accepted
 -o outfile, --outfile outfile
 -f out_format, --format out_format
                       Output format: STATIONXML,TEXT, SACPZ, or KML
 --array array_list    Comma separated list of arrays.
 --station station_list
                       Comma separated list of stations. Wildcards accepted
 --receiver receiver_list
                       Comma separated list of receiver id's. Wildcards
                       accepted
 -c channel_list, --channel channel_list
                       Comma separated list of channels. Wildcards accepted
 --component component_list
                       Comma separated list of components.
Wildcards accepted
 -l location_list, --location location_list
                       Comma separated list of locations.
Wildcards accepted
 -s start_time, --starttime start_time
                       start time in FDSN time format or
PASSCAL time format
 -t end_time, --endtime end_time
                       stop time in FDSN time format or PASSCAL time format
 --level level         Specify level of detail using network, station,
                       channel,or response
 --minlat minlat       Limit to stations with a latitude larger
than or equal
                       to the specified minimum.
 --maxlat maxlat       Limit to stations with a latitude smaller than or
                       equal to the specified maximum.
 --minlon minlon       Limit to stations with a longitude larger than or
                       equal to the specified minimum.
 --maxlon maxlon       Limit to stations with a longitude smaller than or
                       equal to the specified maximum.
 --latitude LATITUDE   Specify the central latitude point for a radial
                       geographic constraint.
 --longitude LONGITUDE
                       Specify the central longitude point for a radial
                       geographic constraint.
 --minradius MINRADIUS
                       Specify minimum distance from the geographic point
                       defined by latitude and longitude.
 --maxradius MAXRADIUS
                       Specify maximum distance from the geographic point
                       defined by latitude and longitude.
 --uri uri"""

        elif args.n == "ph5toexml":
            string = "ph5toexml: ImportError: No module named pykml.factory"
        elif args.n == "ph5_merge_helper":
            string = """usage: ph5_merge_helper [-s miniPH5_start_index]

Modify Index_t.kef and miniPH5_xxxxx.ph5 file names so they can be merged.

optional arguments:
  -h, --help         show this help message and exit
  -s mini_ph5_index  For the first miniPH5_xxxxx.ph5,
      xxxxx should equal the given value.
  -d"""
        elif args.n == "ph5_total":
            string = """Usage: ph5_total -p="<ph5path>" [options]

Find total size of ph5 files in a directory.

optional arguments:
  -h, --help            show this help message and exit
  -n nickname, --nickname nickname
  -p ph5path, --ph5path ph5path"""
        elif args.n == "ph5_validate":
            string = """Usage: ph5validate--nickname="Master_PH5_file"
                [options]

Runs set of checks on PH5 archvive

optional arguments:
  -h, --help            show this help message and exit
  -n nickname, --nickname nickname
  -p ph5_path, --ph5path ph5_path
  -l level, --level level
                        Logging level. Choose from 'error, 'warning', and
                        'info' (default).
  -v, --verbose         Verbose logging."""
        elif args.n == "recreate_external_references":
            string = """Usage: recreate_external_references
                --nickname=ph5-file-prefix

Version: 2018.268 Rebuild external references under
    Receivers_g from info in Index_t.

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Default to current directory."""
        elif args.n == "report_gen":
            string = """Usage: report_gen --nickname=ph5-file-prefix options

Generate data_description.txt and/or data_request_key.txt.

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Default to current directory.
  -k, --key             Write data_request_key.txt.
  -d, --description     Write data_description.txt.
  --debug"""
        elif args.n == "reporttoph5":
            string = """usage: report2ph5 --file report-file
    --nickname experiment-nickname [--path path-to-kef-file][--kef kef-file]

Load a report (pdf) into a ph5 file.

optional arguments:
  -h, --help            show this help message and exit
  -n NICKNAME, --nickname NICKNAME
                        Experiment nickname.
  -p PATH, --path PATH  Path to where ph5 files are stored.
          Defaults to current working directory.
  -f REPORT_FILE, --file REPORT_FILE
                        The file containing the report, (pdf, doc, ps, etc.).
  -k KEF_FILE, --kef KEF_FILE
                        Kef file describing row in Report_t for the report.
                            Not required.
"""
        elif args.n == "resp_load":
            string = """Usage: resp_load  --nickname=Master_PH5_file [options]

This fixes then n_i numbers in the arrays, creates new array.kef files, loads
RESP files into PH5 and creates a new 'response.kef'.

optional arguments:
  -h, --help            show this help message and exit
  -n nickname, --nickname nickname
  -p ph5_path, --ph5path ph5_path
  -a array, --array array
                        Comma separated list of arrays to update
  -i input_csv, --input_csv input_csv
                        input csv. If no input is given a template will be
                        created for you based on the experiment.
"""
        elif args.n == "seg2toph5":
            string = """Usage: seg2toph5 [options]

Read data in SEG-2 revision 1 (StrataVisor) into ph5 format.

optional arguments:
  -h, --help            show this help message and exit
  -f file_list_file, --file file_list_file
                        File containing list of absolute paths to SEG-2 file.
  -n output_file_prefix, --nickname output_file_prefix
                        The ph5 file prefix (experiment nick name).
  -M num_mini, --num_mini num_mini
                        Create a given number of miniPH5 files.
  -S first_mini, --first_mini first_mini
                        The index of the first miniPH5_xxxxx.ph5 file.
  -s samplerate, --samplerate samplerate
                        Extract only data at given sample rate.
  -p                    Do print"""
        elif args.n == "segdtoph5":
            string = """Usage: segd2ph5 [options]

Options:
  -h, --help            show this help message and exit
  -r raw_file, --raw=raw_file
                        Fairfield SEG-D v1.6 file.
  -f INFILE             File containing list of Fairfield SEG-D
                        v1.6 file names.
  -n output_file_prefix, --nickname=output_file_prefix
                        The ph5 file prefix (experiment nick name).
  -U utm_zone, --UTM=utm_zone
                        Locations in SEG-D file are UTM, --UTM=utmzone. Zone
                        number and N or S designation eg 13N
  -T, --TSPF            Locations are in texas state plane coordinates.
  -M num_mini, --num_mini=num_mini
                        Create a given number of miniPH5 files.
  -S first_mini, --first_mini=first_mini
                        The index of the first miniPH5_xxxxx.ph5 file.
  -c combine, --combine=combine
                        Combine this number if SEG-D traces to one
                        PH5 trace.
  -E, --allevents
  --manufacturers_code=MANUFACTURERS_CODE
                        Manufacturers code. Defaults to 20 for Fairfield.
                        Most likely will not work for SEG-D written by other
                        data loggers,"""
        elif args.n == "segytoph5":
            string = """Read a standard SEG-Y file and load it into a PH5 file.

Version: 2018.268

optional arguments:
  -h, --help            show this help message and exit
  -f INFILE             Input SEG-Y file.
  -n output_file_prefix, --nickname output_file_prefix
                        The ph5 file prefix (experiment nick name).
  -S, --recv-order      The SEG-Y input file is in receiver order.
  -t {U,P,S,N,I}        Extended trace header style. U => USGS Menlo,
          P => PASSCAL, S => SEG, I => SIOSEIS, N => iNova FireFly
  -p
  -L BYTES_PER_TRACE    Force bytes per trace. Overrides header values.
  -T TRACES_PER_ENSEMBLE
                        Force traces per ensemble. Overrides header value.
  -F TRACE_FORMAT       1 = IBM - 4 bytes, 2 = INT - 4 bytes,
        3 = INT - 2 bytes,v   5 = IEEE - 4 bytes, 8 = INT - 1 byte.
            Override header value.
  -e ENDIAN             Endianess: 'big' or 'little'. Default = 'big'.
      Override header value.
  -i                    EBCDIC textural header. Override header value.
  -d DAS                Set station ID for all traces, otherwise field
                          trace number is used.
  -3                    The gather contains data recorded using
                          3 channels, 1, 2, 3.
"""
        elif args.n == "set_deploy_pickup_times":
            string = """Set deploy and pickup times in an Array_t_xxx.kef file.

Usage:  set_deploy_pickup_times -a Array_t_xxx.kef
            -d ASCII_deploy_time -p ASCII_pickup_time

optional arguments:
  -h, --help            show this help message and exit
  -a array_kef, --array-kef array_kef
                        The Array_t_xxx.kef file to modify.
  -d deploy_time, --deploy-time deploy_time
                        Array deployment time: YYYY:JJJ:HH:MM:SS
  -p pickup_time, --pickup-time pickup_time
                        Array pickup time: YYYY:JJJ:HH:MM:SS"""
        elif args.n == "set_n_i_response":
            string = """Updating the response table references
                for multiple instrument types.

Usage: set_n_i_response    (Run from top level families directory.)

Skip this step if you only have one type of instrumentation.
In your PH5 directory containing the sub families and Sigma directory run:
>> set_n_i_response
This will create a new directory called RESPONSE_T_N_I.
Move into this directory. From the RESPONSE_T_N_I directory run:
 >> load_das_t --path=../Sigma --onlysave
 >> loadd_das_t --path=../Sigma --onlyload
Delete the old response table and load the new Response_t_cor.kef file
    found in the RESPONSE_T_N_I directory.
>> delete_table –n ../Sigma/master.ph5 –R
 >> keftoph5 –n ../Sigma/master.ph5 –k Response_t_cor.kef

optional arguments:
  -h, --help            show this help message and exit
  -F FAMILIES_DIRECTORY
                        Directory that holds the family directories'
                        Absolute path.
  -N FIRST_N_I          The n_i of the first entry. Defaults to zero."""
        elif args.n == "sort_kef_gen":
            string = """Generate a kef file to populate Sort_t.

Usage: sort_kef_gen --nickname ph5-file-prefix
    --serial-number DAS-SN | --auto [--path path-to-ph5-files]

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Defaults to current directory.
  -s sn, --serial-number sn
                        DAS to use to get windows.
  -a, --auto            Attempt to auto detect windows.
                          Windows should start at the same time on all DASs.
  -d, --debug

"""
        elif args.n == "sort_array_t":
            string = """Sort an Array_t_xxx.kef file by station ID, id_s.

usage: sort_array_t Array_t_unsorted.kef -f Array_t_unsorted.kef

optional arguments:
  -h, --help            show this help message and exit
  -f INFILE, --file INFILE
                        KEF file containing unsorted stations.
  -o OUTFILE, --outfile OUTFILE
                        Sorted KEF file create. Defaults to stdout.
"""
        elif args.n == "ph5tokef":
            string = """Dump a table to a kef file.

usage: tabletokef     --nickname ph5-file-prefix options

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Default to current directory.
  -u update_key, --update_key update_key
                        Set generated kef file to do an Update on key.
  -d, --debug
  -E, --Experiment_t    Dump /Experiment_g/Experiment_t to a kef file.
  -S, --Sort_t          Dump /Experiment_g/Sorts_g/Sort_t to a kef file.
  -O a_e, --Offset_t a_e
                        Dump /Experiment_g/Sort_g/Offset_t_[arrayID_eventID]
                            to a kef file.
  -V n, --Event_t_ n    Dump /Experiment_g/Sorts_g/Event_t_[n]
                            to a kef file.
  --all_events          Dump all /Experiment_g/Sorts_g/Event_t_xxx
                            to a kef file.
  -A n, --Array_t_ n    Dump /Experiment_g/Sorts_g/Array_t_[n]
                            to a kef file.
  --all_arrays          Dump all /Experiment_g/Sorts_g/Array_t_xxx
                            to a kef file.
  -R, --Response_t      Dump /Experiment_g/Responses_g/Response_t
                            to a kef file.
  -P, --Report_t        Dump /Experiment_g/Reports_g/Report_t
                            to a kef file.
  -C, --Receiver_t      Dump /Experiment_g/Receivers_g/Receiver_t
                            to a kef file.
  -I, --Index_t         Dump /Experiment_g/Receivers_g/Index_t
                              to a kef file.
  -M, --M_Index_t       Dump /Experiment_g/Maps_g/Index_t
                              to a kef file.
  -D das, --Das_t das   Dump /Experiment_g/Receivers_g/Das_g_[das]/Das_t
                            to a kef file.
  -T, --Time_t          Dump /Experiment_g/Receivers_g/Time_t
                            to a kef file.
"""
        elif args.n == "time_kef_gen":
            string = """Generates kef file to populate Time_t from SOH_A_.

usage: time-kef-gen --nickname ph5-file-prefix     [-p path]

Calculate clock drift from texan data previously
loaded into a family of ph5 files and produce a
kitchen exchange format (KEF) file containing
clock correction information. The KEF file can
then be loaded directly into the family of ph5
files.

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files Defaults current directory.
  -r, --clock_report    Write clock performance log, time-kef-gen.log

"""
        elif args.n == "tabletokef":
            string = """Dump a table to a kef file.

usage: tabletokef     --nickname ph5-file-prefix options

optional arguments:
  -h, --help            show this help message and exit
  -n ph5_file_prefix, --nickname ph5_file_prefix
                        The ph5 file prefix (experiment nickname).
  -p ph5_path, --path ph5_path
                        Path to ph5 files. Default to current directory.
  -u update_key, --update_key update_key
                        Set generated kef file to do an Update on key.
  -d, --debug
  -E, --Experiment_t    Dump /Experiment_g/Experiment_t to a kef file.
  -S, --Sort_t          Dump /Experiment_g/Sorts_g/Sort_t to a kef file.
  -O a_e, --Offset_t a_e
                        Dump /Experiment_g/Sort_g/Offset_t_[arrayID_eventID]
                            to a kef file.
  -V n, --Event_t_ n    Dump /Experiment_g/Sorts_g/Event_t_[n]
                            to a kef file.
  --all_events          Dump all /Experiment_g/Sorts_g/Event_t_xxx
                            to a kef file.
  -A n, --Array_t_ n    Dump /Experiment_g/Sorts_g/Array_t_[n]
                            to a kef file.
  --all_arrays          Dump all /Experiment_g/Sorts_g/Array_t_xxx
                            to a kef file.
  -R, --Response_t      Dump /Experiment_g/Responses_g/Response_t
                            to a kef file.
  -P, --Report_t        Dump /Experiment_g/Reports_g/Report_t
                            to a kef file.
  -C, --Receiver_t      Dump /Experiment_g/Receivers_g/Receiver_t
                            to a kef file.
  -I, --Index_t         Dump /Experiment_g/Receivers_g/Index_t
                            to a kef file.
  -M, --M_Index_t       Dump /Experiment_g/Maps_g/Index_t to a kef file.
  -D das, --Das_t das   Dump /Experiment_g/Receivers_g/Das_g_[das]/Das_t
                            to a kef file.
  -T, --Time_t          Dump /Experiment_g/Receivers_g/Time_t to a kef file.

"""
        elif args.n == "unsimpleton":
            string = """A command line utility to link fairfield
SEG-D file names that expose information about the contents of the file,
ie. makes file names for carbon units.

optional arguments:
  -h, --help            show this help message and exit
  -f SEGDFILELIST, --filelist SEGDFILELIST
                        The list of SEG-D files to link.
  -d LINKDIRECTORY, --linkdir LINKDIRECTORY
                        Name directory to place renamed links.
  --hardlinks           Create hard links inplace of soft links.
"""
        else:
            print
            print "Usage: ph5 name {subprogram name}"
            if len(args.n) > 0:
                print "The name '{}' is not supported.".format(args.n)
                print "Type ph5 with no arguments to see the full list."

        print string

    except ValueError or TypeError:
        showlist()

    print
    print


def showlist():
    string = """
Enter the name of a subprogram to see details,
e.g. type '$ ph5 ph5toevt' to see info for ph5toevt.
Available subprograms:

GUI scripts:  # clients
ph5view, noven, pforma, kefedit, experiment_t_gen

CONSOLE scripts:"  # utilities
125atoph5, 130toph5, cross_check_event_array_data, csvtokef,
geo_kef_gen, graotoph5, index_offset_t, initialize_ph5, keftocsv,
keftokml, keftoph5, load_das_t, meta_data_gen, nuke_table,
delete_table, pformacl, ph5toevt, ph5toms, ph5torec,
ph5tostationxml, ph5toexml, ph5_merge_helper, ph5_total,
ph5_validate, recreate_external_references, report_gen,
reporttoph5, resp_load, seg2toph5, segytoph5,
set_deploy_pickup_times, set_n_i_response, sort_kef_gen,
sort_array_t, ph5tokef, time_kef_gen, tabletokef, unsimpleton """
    print string
    return


if __name__ == '__main__':
    main()
