#!/usr/bin/env pnpython3
#
# Steve Azevedo, July 2015
#

import os
import sys
import logging
import exceptions
import json
import time
import subprocess32 as subprocess

from zlib import adler32
import re

from ph5.core import segdreader_smartsolo

PROG_VERSION = '2024.249'
LOGGER = logging.getLogger(__name__)

HOME = os.environ['HOME']
DOT = os.path.join(HOME, '.pforma')
JSON_DB = 'pforma.json'
JSON_CFG = 'pforma.cfg'

PROG2INST = {'125atoph5': 'texan', '130toph5': 'rt-130',
             'segdtoph5': 'nodal', 'seg2toph5': 'seg2'}
INST2PROG = {'texan': '125atoph5', 'rt-130': '130toph5',
             'nodal': 'segdtoph5', 'seg2': 'seg2toph5'}

ON_POSIX = 'posix' in sys.builtin_module_names


class FormaIOError(exceptions.Exception):
    def __init__(self, errno, msg):
        self.errno = errno
        self.message = msg


class FormaIO():
    '''
        Create a project to read RAW data into a PH5 file in parallel.
    '''
    # These are the number of conversions that can be run at once.
    MINIS = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
             'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
             'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
             'Y', 'Z', 'AA', 'BB', 'CC', 'DD', 'EE', 'FF',
             'GG', 'HH', 'II', 'JJ', 'KK', 'LL', 'MM', 'NN',
             'OO', 'PP', 'QQ', 'RR', 'SS', 'TT', 'UU', 'VV',
             'WW', 'XX', 'YY', 'ZZ', 'AAA', 'BBB', 'CCC', 'DDD',
             'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ', 'LLL', 'MMM')

    def __init__(self, infile=None, outdir=None, main_window=None):
        self.main_window = main_window
        self.infile = infile  # Input file (list of raw files)
        self.infh = None  # File handle for infile
        self.raw_files = {}  # Raw files organized by type
        self.file_das_type = {}  # Das, type by file paths
        self.total_raw = 0.0  # Total size of raw
        self.number_raw = 0
        self.home = outdir  # Where the processing of the ph5 files happens
        self.whereami = os.getcwd()  # Where the program was started
        self.M = None  # How many mini files in each ph5 family
        self.UTM = None  # UTM zone (SEG-D)
        self.TSPF = None  # texas state plane coordinates (SEG-D)
        self.COMBINE = 1  # Combine traces from SEG-D file
        self.read_cfg()  # Configuration info
        if self.cfg and 'M' in self.cfg:
            self.M = int(self.cfg['M'])

        if self.cfg and 'N' in self.cfg:
            self.nmini = FormaIO.MINIS[0:self.cfg['N']]
        else:
            self.nmini = FormaIO.MINIS[0:4]

    def set_cfg(self):
        '''
            Set the location of the configuration file.
            Should get kept in the project.
            Contains:
                      JSON_DB -> Path to files already read into PH5 family
                      M -> How many mini files to build in each family
                      N -> How many families of PH5 files to create
        '''
        self.cfg = {}
        self.cfg['JSON_DB'] = os.path.join(self.home, JSON_DB)
        self.cfg['M'] = self.M
        self.cfg['N'] = len(self.nmini)

    def set_utm(self, utm):
        self.UTM = utm

    def set_combine(self, combine):
        self.COMBINE = combine

    def set_tspf(self, tspf):
        self.TSPF = tspf

    def read_cfg(self):
        '''
            Read the configuration file.
        '''
        self.cfg = read_json(os.path.join(self.home, JSON_CFG))
        # print 'CFG', self.cfg
        if self.cfg is None:
            self.cfg = {}

    def write_cfg(self):
        '''
            Write the config file.
        '''
        self.set_cfg()
        write_json(self.cfg, os.path.join(self.home, JSON_CFG))

    def set_nmini(self, n):
        '''
            Set the self.nmini list of PH5 families from n and FormaIO.MINIS.
            Use value for N from pforma.cfg if it exists.
        '''
        if 'N' not in self.cfg:
            self.nmini = FormaIO.MINIS[0:n]

    def initialize_ph5(self):
        '''   Set up processing directory structure and set M from
              existing mini files   '''
        if self.home is None:
            return
        if not os.path.exists(self.home):
            try:
                os.makedirs(self.home)
            except Exception:
                raise FormaIOError(
                    4,
                    "Failed to create output directory: {0}".format(self.home))

        for m in self.nmini:
            os.chdir(self.home)
            if not os.path.exists(m):
                os.mkdir(m)

            try:
                os.chdir(m)
                subprocess.call('initialize_ph5 -n master', shell=True,
                                stdout=open(os.devnull, 'w'),
                                stderr=open(os.devnull, 'w'))
            except Exception:
                raise FormaIOError(5, "Failed to initialize {0}".format(
                    os.path.join(self.home, m)))

            files = os.listdir('.')
            minis =\
                filter(lambda a: a[0:5] == 'miniP' and a[-3:] == 'ph5', files)
            if len(minis):
                if self.M is None or len(minis) > self.M:
                    self.M = len(minis)

        os.chdir(self.whereami)

    def set_M(self, m):
        '''
            Set self.M, the number of mini files in each family.
        '''
        try:
            self.M = int(m)
        except Exception as e:
            raise FormaIOError(
                errno=10, msg="Failed to set M: {0}".format(e.message))

    def run_simple(self, cmds, x, family):
        '''
            Run a single command in a subprocess. Line buffer output.
            cmds   -> A list of commands to be run for this family
            x      -> The sequence of the command to run
            family -> The family that goes with these commands
            pee    -> The process
            fifofh -> File handle to fifo
        '''
        pee = None
        try:
            cmd = cmds[x]
        except IndexError:
            return pee, None

        pee = subprocess.Popen(cmd,
                               shell=True,
                               bufsize=1,
                               cwd=os.path.join(self.home, family),
                               stdout=subprocess.PIPE,
                               universal_newlines=True,
                               close_fds=ON_POSIX)
        fifofh = pee.stdout

        return pee, fifofh

    def run_cmds(self, cmds, x=0, ems=None):
        '''
            Run conversion commands in a subprocess
            cmds -> A dictionary of families that point to a list of commands.
                    cmds['B']['texan2ph5 -n master.ph5 ...', '1302ph5 -n
                     master.ph5 ...']
            x -> The sequence of the current command executing in
             the list in cmds.
            ems -> The list of families ['A', 'B', 'C' etc]
        '''
        pees = {}
        if ems is None:
            ems = self.nmini
        else:
            ems = [ems]
        for m in ems:
            if len(cmds[m]) > x:
                insts = cmds[m][x]
                pees[m] = subprocess.Popen(insts,
                                           shell=True,
                                           bufsize=-1,
                                           cwd=os.path.join(self.home, m),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

            else:
                pees[m] = None
        if len(ems) > 1:
            return pees, x
        else:
            return pees[m], x

    #
    # Should this be implemented as a closure?
    #

    def run(self, runit=True):
        '''   Run processes to convert raw files to ph5
              runit -> If true, execute processes otherwise only return list of
              commands to execute.
        '''

        def split(ts):
            '''   Split up lists of raw files for processing.
                  Key by mini ph5 family name.
            '''
            ret = {}  # Files to load
            tot = {}  # Total raw size per family
            # Initialize
            for m in self.nmini:
                ret[m] = {}
                tot[m] = 0

            # Check to see if any of these are already loaded (data from a das
            # must all be in the same family).
            dass = self.resolved.keys()
            for d in dass:
                raws = self.resolved[d]
                for r in raws:
                    if r['mini'] and r['mini'] in ret:
                        if d not in ret[r['mini']]:
                            ret[r['mini']][d] = []

                        tot[r['mini']] += r['size']
                        ret[r['mini']][d].append(r)

            # Go through remaining dass and assign them to a family
            dass.sort()
            i = 0
            for d in dass:
                raws = self.resolved[d]
                if tot[self.nmini[i]] >= ts:
                    i += 1
                    if i > len(self.nmini) - 1:
                        i -= 1

                for r in raws:
                    if r['mini']:
                        continue

                    if d not in ret[self.nmini[i]]:
                        ret[self.nmini[i]][d] = []

                    r['mini'] = self.nmini[i]
                    tot[self.nmini[i]] += r['size']
                    ret[self.nmini[i]][d].append(r)

            return ret

        def setup(tl):
            '''   Write sub-lists of raw files to each mini
                  family directory   '''
            ret = {}
            for m in self.nmini:
                ret[m] = {}
                for typ in ('texan', 'rt-130', 'nodal', 'seg2'):
                    of = None
                    outfile = "{0}_{1}{2}.lst".format(
                        typ, str(int(time.time())), m)
                    os.chdir(os.path.join(self.home, m))
                    dass = tl[m]
                    keys = sorted(dass.keys())
                    wrote = False
                    for d in keys:
                        files = dass[d]
                        for f in files:
                            if f['type'] == typ:
                                if not of:
                                    of = open(outfile, 'w+')
                                of.write(f['path'] + '\n')
                                wrote = True

                    try:
                        of.close()
                    except BaseException:
                        pass
                    if wrote:
                        ret[m][typ] = os.path.join(self.home, m, outfile)

            os.chdir(self.whereami)

            return ret

        def build_cmds(lsts):
            '''   Make commands to do the conversion from raw to ph5
                  for each mini ph5 family   '''
            ret = {}
            info = {}

            i = 0
            for m in self.nmini:
                cmd = []
                lists = []
                instruments = []
                lst = lsts[m]
                if not self.M:
                    self.M = 1
                ess = i * self.M + 1
                if 'texan' in lst:
                    lists.append(lst['texan'])
                    instruments.append('texan')
                    clprog = INST2PROG['texan']
                    cmd.append(
                        "{3} -n master.ph5 -f {0} -M {1} -S {2}\
                         --overide 2>&1".format(lst['texan'],
                                                self.M, ess, clprog))
                if 'rt-130' in lst:
                    lists.append(lst['rt-130'])
                    instruments.append('rt-130')
                    clprog = INST2PROG['rt-130']
                    cmd.append(
                        "{3} -n master.ph5 -f {0} -M {1} -S {2} 2>&1".format(
                            lst['rt-130'], self.M, ess, clprog))

                if 'seg2' in lst:
                    lists.append(lst['seg2'])
                    instruments.append('seg2')
                    clprog = INST2PROG['seg2']
                    cmd.append(
                        "{3} -n master.ph5 -f {0} -M {1} -S {2} 2>&1".format(
                            lst['seg2'], self.M, ess, clprog))

                if 'nodal' in lst:
                    lists.append(lst['nodal'])
                    instruments.append('nodal')
                    clprog = INST2PROG['nodal']
                    if self.UTM:
                        cmd.append(
                            "{5} -n master.ph5 -f {0} -M {1} -U {3} -S {2} -c\
                             {4} 2>&1".format(lst['nodal'], self.M,
                                              ess, self.UTM, self.COMBINE,
                                              clprog))
                    elif self.TSPF:
                        cmd.append(
                            "{4} -n master.ph5 -f {0} -M {1} -T -S {2} -c\
                             {3} 2>&1".format(
                                lst['nodal'], self.M, ess, self.COMBINE,
                                clprog))
                    else:
                        cmd.append(
                            "{4} -n master.ph5 -f {0} -M {1} -S {2} -c\
                             {3} 2>&1".format(
                                lst['nodal'], self.M, ess, self.COMBINE,
                                clprog))
                ret[m] = cmd
                if m not in info:
                    info[m] = {}

                info[m]['lists'] = lists
                info[m]['instruments'] = instruments

                i += 1

            return ret, info

        def save_cmds(cmds):
            '''   Save commands   '''
            write_json(cmds, os.path.join(
                self.home, "commands{0}.json".format(str(int(time.time())))))

        #
        # Main
        #
        target_size = self.total_raw / len(self.nmini)
        toload = split(target_size)
        lsts = setup(toload)
        cmds, info = build_cmds(lsts)
        save_cmds(cmds)
        if runit is True:
            pees, i = self.run_cmds(cmds)
            return cmds, pees, i
        else:
            return cmds, info, None

    def open(self):
        '''   Open file containing list of raw files   '''
        if self.infile is None:
            return

        try:
            self.infh = open(self.infile, "Ur")
        except Exception:
            self.infh = None
            raise FormaIOError(
                errno=1, msg="Failed to open: {0}.".format(self.infile))

    def read(self):
        '''   Read raw files   '''
        if self.infh is None:
            try:
                self.open()
            except FormaIOError as e:
                LOGGER.error("{0}: {1}".format(e.errno, e.message))
                sys.exit()
        if self.infh is None:
            return
        n = 0
        while True:
            line = self.infh.readline()
            if not line:
                break
            # Skip commented lines
            if line[0] == '#':
                continue
            line = line.strip()
            # Skip empty line
            if not line:
                continue
            line_parts = line.split(':')
            file_abs_path = line_parts[0]
            # Skip files that do not exist
            if not os.path.exists(file_abs_path):
                LOGGER.warning(
                    "{0} not found. Skipping.".format(file_abs_path))
                continue
            n += 1

            # Try to guess data logger type and serial number based on file
            # name
            raw_file = os.path.basename(file_abs_path)
            if len(line_parts) > 1:
                tp, das = 'nodal', line_parts[1]
            else:
                tp, das = guess_instrument_type(raw_file, file_abs_path,
                                                self.main_window)
            if das == 'lllsss':
                raise FormaIOError(
                    errno=4,
                    msg="May be nodal SEG-D file but using simpleton file\
                     naming scheme. Please rename.")
            if tp == 'unknown':
                raise FormaIOError(errno=3,
                                   msg=("File in {1} does not have standard "
                                        "name: {0}").format(
                                       raw_file, self.infile))
            if tp == 'rt-130':
                raise FormaIOError(errno=5,
                                   msg=("{0}: RT130 data detected, exit and "
                                        "add data to PH5 with 130toph5."
                                        ).format(raw_file))
            if tp == 'seg2':
                raise FormaIOError(errno=5,
                                   msg=("{0}: SEG2 data detected, exit and "
                                        "add data to PH5 with seg2toph5."
                                        ).format(raw_file))

            # Save info about each raw file keyed by serial number in
            # self.raw_files
            if das not in self.raw_files:
                self.raw_files[das] = []

            file_info = {}
            # Type of data logger
            file_info['type'] = tp
            # Full path to raw file
            file_info['path'] = file_abs_path
            # Size of raw file in bytes
            file_info['size'] = os.stat(file_abs_path).st_size
            # Time file was modified
            file_info['mtime'] = os.stat(file_abs_path).st_mtime
            # file_info['adler'] = check_sum (line)
            # Which family of ph5 files does this belong to. See self.nmini
            file_info['mini'] = None
            # Total of raw files so far in bytes
            self.total_raw += file_info['size']
            self.raw_files[das].append(file_info)
            self.file_das_type[file_abs_path] = {'das': das, 'type': tp}
        self.average_raw = int(self.total_raw / n)
        self.number_raw = n
        self.infh.close()
        # Estimate M so each mini file is about 12GB
        if self.M is None:
            self.M = int(
                (((self.total_raw / len(
                    self.nmini)) / 1024 / 1024 / 1024) / 12) + 0.5)
            if self.M == 0:
                self.M = 1

    def readDB(self):
        '''   Read JSON file containing files loaded so far. Same format as
              self.raw_files   '''
        try:
            self.db_files = read_json(os.path.join(self.home, JSON_DB))
        except Exception as e:
            self.db_files = {}
            raise FormaIOError(
                2, "Failed to read {0}. {1}".format(self._json, e.message))

    def resolveDB(self):
        '''   Resolve the list of raw files with the files already loaded   '''
        new_keys = sorted(self.raw_files.keys())

        existing_keys = self.db_files.keys()
        if len(existing_keys) == 0:
            self.resolved = self.raw_files
            return

        existing_keys.sort()

        ret = {}
        n_save = []
        # Loop on DAS SN
        for nk in new_keys:
            # List of dictionaries
            new_dass = self.raw_files[nk]
            # We have seen this DAS before
            if nk in existing_keys:
                existing_dass = self.db_files[nk]
                for n in new_dass:
                    n_base = os.path.basename(n['path'])
                    for e in existing_dass:
                        e_base = os.path.basename(e['path'])
                        # File names and sizes match, so calculate checksum
                        if e_base == n_base and e['size'] == n['size']:
                            e_adler = check_sum(e['path'])
                            n_adler = check_sum(n['path'])
                            # Checksums don't match so save
                            if e_adler != n_adler:
                                n['mini'] = e['mini']
                                n_save.append(n)
                        # Appears to be different file so save
                        else:
                            n['mini'] = e['mini']
                            n_save.append(n)

                # Save this file, we will need to load it
                if len(n_save) != 0:
                    ret[nk] = n_save
                    n_save = []

            # Have not seen this DAS yet
            else:
                ret[nk] = new_dass

        self.resolved = ret

    def unite(self, TO='A'):
        '''   Unite all of the ph5 families to one. Move everything to 'A'
        '''
        from shutil import copy2

        def _wait_for_it(P):
            while True:
                somerunning = False
                for p in P:
                    p.poll()
                    if p.returncode is None:
                        somerunning = True
                    elif p.returncode != 0:
                        LOGGER.error("Process {0} failed.".format(p.args))

                if somerunning is False:
                    return

        def get_index():
            '''   Read /Experiment_g/Receivers_g/Index_t   '''
            msg = []
            P = []
            for m in self.nmini:
                os.chdir(os.path.join(self.home, m))
                command = "ph5tokef -n master.ph5 -I > Index_t.kef"
                ret = subprocess.Popen(
                    command, shell=True, stderr=open(os.devnull, "w"))
                P.append(ret)
                msg.append("Extracting Index_t for {0}".format(m))
            os.chdir(self.whereami)
            _wait_for_it(P)

            return msg

        def load_index():
            '''   Load all Index_t files into the TO family   '''
            msg = []
            P = []
            if not os.path.exists(os.path.join(self.home, TO)):
                os.mkdir(os.path.join(self.home, TO))

            os.chdir(os.path.join(self.home, TO))
            for m in self.nmini:
                if m == 'A' and TO != 'A':
                    try:
                        copy2('../A/master.ph5', './master.ph5')
                        # index_t already in Sigma/master.ph5 after copied
                        # -> skip loading into it
                        continue
                    except BaseException:
                        raise FormaIOError(
                            errno=7,
                            msg="Failed to copy A/master.ph5 to\
                             {0}/master.ph5.".format(
                                TO))

                command = "keftoph5 -n master.ph5 -k ../{0}/Index_t.kef"\
                    .format(m)
                ret = subprocess.Popen(
                    command, shell=True, stderr=open(os.devnull, "w"))
                P.append(ret)
                # Load one at a time
                _wait_for_it(P)
                msg.append(
                    "Extracted Index_t from {0} and loading into\
                     {1}/master.ph5.".format(m, TO))

            os.chdir(self.whereami)

            return msg

        def get_array():
            '''   Dump /Experiment_g/Sorts_g/Array_t_xxx to Array_t_cat.kef
            '''
            msg = []
            P = []
            for m in self.nmini:
                os.chdir(os.path.join(self.home, m))
                command = "ph5tokef -n master.ph5 --all_arrays>Array_t_cat.kef"
                ret = subprocess.Popen(
                    command, shell=True, stderr=open(os.devnull, "w"))
                P.append(ret)
                msg.append(
                    "Extracting all Array_t for {0} to Array_t_cat.kef".format(
                        m))
            os.chdir(self.whereami)
            _wait_for_it(P)

            return msg

        def load_array():
            '''   Load Array_t_cat files into the TO family   '''
            msg = []
            P = []

            os.chdir(os.path.join(self.home, TO))
            for m in self.nmini:
                if m == 'A' and TO != 'A':
                    # already added this table in load_index when copy
                    # master.ph5 from A to/ TO/
                    continue
                command = "keftoph5 -n master.ph5 -k ../{0}/Array_t_cat.kef"\
                    .format(m)
                ret = subprocess.Popen(
                    command, shell=True, stderr=open(os.devnull, "w"))
                P.append(ret)
                # Load one at a time
                _wait_for_it(P)
                msg.append(
                    "Extracted Array_t_cat from {0} and loading into\
                     {1}/master.ph5.".format(m, TO))

            os.chdir(self.whereami)

            return msg

        def move_minis():
            '''   Move all the mini ph5 files to the TO family   '''
            msg = []
            os.chdir(os.path.join(self.home, TO))
            for m in self.nmini:
                print m

                minis = os.listdir("../{0}".format(m))
                for mini in minis:
                    if mini[0:5] == 'miniP' and not os.path.islink(mini):
                        try:
                            os.link("../{0}/{1}".format(m, mini), mini)
                        except Exception:
                            raise FormaIOError(
                                errno=8,
                                msg="Failed to move {0} to A.".format(mini))

                        print "Hard link {0} to {2}, preserve {1}/master.ph5."\
                            .format(mini, m, TO)
                        msg.append("Hard link {0} to {2}, preserve\
                         {1}/master.ph5.".format(mini, m, TO))

            os.chdir(self.whereami)
            return msg

        def recreate_references():
            '''   Recreate extermal references in /Experiment_g/Receivers_g
            '''
            msg = []
            P = []
            os.chdir(os.path.join(self.home, TO))
            # Create a copy of the original master file
            copy2('../A/master.ph5', '../A/master_original.ph5')
            command = "recreate_external_references -n master.ph5"
            ret = subprocess.Popen(command, shell=True, stdout=open(
                os.devnull, "w"), stderr=open(os.devnull, "w"))
            P.append(ret)

            msg.append(
                "Recreated external references in {0}/master.ph5.".format(TO))

            os.chdir(self.whereami)
            _wait_for_it(P)
            return msg

        msg = []
        msg.extend(get_index())
        msg.extend(load_index())
        msg.extend(get_array())
        msg.extend(load_array())
        msg.extend(move_minis())
        msg.extend(recreate_references())
        return msg

    def merge(self, loaded_dass):
        '''   Merge list of raw loaded with already loaded and re-write JSON_DB
        '''
        # What was already loaded
        db_dass = self.db_files.keys()
        # What we just loaded
        # loaded_dass = self.resolved.keys ()
        for das in loaded_dass:
            if das not in db_dass:
                self.db_files[das] = []

            for r in self.resolved[das]:
                self.db_files[das].append(r)

        write_json(self.db_files, os.path.join(self.home, JSON_DB))


#
# Mixins
#

def check_sum(filename):
    fd = os.open(filename, os.O_RDONLY)
    cs = 1
    while True:
        buf = os.read(fd, 268435456)
        if not buf:
            break
        cs = adler32(buf, cs)

    os.close(fd)
    return cs & 0xffffffff


# For type 'texan'
texanRE = re.compile(r"[Ii](\d\d\d\d).*[Tt][Rr][Dd]")
# For type 'seg2'
seg2RE = re.compile(r"(\d+)\.dat")
# For type 'rt-130'
rt130RE = re.compile(r"\d\d\d\d\d\d\d\.(\w\w\w\w)(\.\d\d)?\.[Zz][Ii][Pp]")
# ============================= SEGD ============================== #
# For type 'nodal'
nodalRE = re.compile(r"[Rr](\d+)_(\d+)\.\d+\.\d+\.[Rr][Gg](\d+)")
# For simpleton 'nodal'
simpletonodalRE = re.compile(r"\d+\.fcnt")
# For type SmartSolo (except for RE, it is still understood as 'nodal')
martSoloRE = re.compile(r"(\d+)[\d.]+.[ENZenz].segd")
# =========================== END SEGD ============================= #
# For PIC rename
picnodalRE = re.compile(r"PIC_(\d+)_(\d+)_\d+\.\d+\.\d+\.[Rr][Gg](\d+)")


def guess_instrument_type(filename, abs_path, main_window=None):
    '''   Attempt to determine type of datalogger from data file name   '''
    mo = texanRE.match(filename)
    if mo:
        das = str(int(mo.groups()[0]) + 10000)
        return 'texan', das
    mo = rt130RE.match(filename)
    if mo:
        das = mo.groups()[0]
        return 'rt-130', das
    mo = nodalRE.match(filename)
    if mo:
        a, b, c = mo.groups()
        das = a + 'X' + b
        return 'nodal', das
    mo = picnodalRE.match(filename)
    if mo:
        a, b, c = mo.groups()
        das = a + 'X' + b
        return 'nodal', das
    mo = simpletonodalRE.match(filename)
    if mo:
        return 'nodal', 'lllsss'
    mo = martSoloRE.match(filename)
    if mo:
        if main_window is None:
            print("Reading SmartSolo header from {0}... Please wait.".format(
                    filename))
        else:
            main_window.statsig.emit(
                "Reading SmartSolo header from {0}... Please wait.".format(
                    filename))
        array, station = get_smartsolo_array_station(abs_path)
        if main_window is not None:
            main_window.statsig.emit("")
        das = array + 'X' + station
        return 'nodal', das
    mo = seg2RE.match(filename)
    if mo:
        das = mo.groups()[0]
        return 'seg2', das
    return 'unknown', None


def get_smartsolo_array_station(path2file):
    """
    Read array_id and station_id from header of the given file.

    :param path2file: absolute path to the file to get the info
    :return array_id: id of the array of the data
    :return station_id: id of the station of the data
    """
    try:
        sd = segdreader_smartsolo.Reader(infile=path2file)
    except BaseException:
        LOGGER.error(
            "Failed to properly read {0}.".format(path2file))
        sys.exit()
    sd.process_general_headers()
    sd.process_channel_set_descriptors()
    sd.process_extended_headers()
    sd.process_external_headers()
    sd.process_trace_headers()
    array_id = sd.trace_headers.line_number
    station_id = sd.trace_headers.receiver_point
    return str(array_id), str(station_id)


def write_json(x, filename):
    '''   Write x in JSON format to filename   '''
    fh = open(filename, 'w')
    json.dump(x, fh, indent=4, sort_keys=True)
    fh.close()


def read_json(filename):
    '''   Read JSON file filename and return object x   '''
    try:
        fh = open(filename)
        x = json.load(fh)
        fh.close()
    except Exception:
        x = {}

    return x


def print_it(x):
    '''   Print JSON to screen   '''
    print json.dumps(x, indent=4, sort_keys=True)


#
# Debug and example follows
#
if __name__ == '__main__':
    filename = "PIC_1_25_1941.0.0.rg16"
    print guess_instrument_type(filename, '.')
    sys.exit()

    import timedoy

    # 2015-08-10 18:18:59,197 Processing:
    # /home/azevedo/Salt/Raw/D069-10Mar/Greg/I1700RAWDO69.TRD...
    processRE = re.compile(
        r"(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\,\d\d\d Processing:\
         (.*[TtZz][RrIi][DdPp])\.\.\..*")
    doneRE = re.compile(
        r"(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d).*nodes recreated\..*")

    fio = FormaIO(infile='./trd2.lst', outdir='/storage/Salt')
    fio.initialize_ph5()

    try:
        fio.open()
    except FormaIOError as e:
        print e.errno, e.message

    try:
        fio.read()
        print "Total raw: {0}GB".format(
            int(fio.total_raw / 1024 / 1024 / 1024))
        print "M:", fio.M
        time.sleep(10)
    except FormaIOError as e:
        print e.errno, e.message

    try:
        fio.readDB()
    except FormaIOError as e:
        print e.errno, e.message
        sys.exit(-1)

    fio.resolveDB()

    # Load raw data
    cmds, pees, i = fio.run()
    # Debug
    ll = {'A': i, 'B': i, 'C': i, 'D': i, 'E': i, 'F': i, 'G': i, 'H': i,
          'I': i, 'J': i, 'K': i, 'L': i, 'M': i, 'N': i, 'O': i, 'P': i}
    cnt = 0
    out = {}
    err = {}
    fifo = {}
    xterms = {}
    running = True
    for m in fio.nmini:
        fifo[m] = "/tmp/fifo{0}".format(m)
        if not os.path.exists(fifo[m]):
            os.mkfifo(fifo[m])

        xterms[m] = subprocess.Popen(
            ['xterm', '-T', m, '-e', 'tail', '-f', fifo[m]])

    while running:
        running = False
        for m in fio.nmini:
            if pees[m] is None:
                continue
            print m, pees[m].pid, 'running' if pees[m].poll(
            ) is None else pees[m].poll()
            if pees[m].poll() == 0:
                ll[m] += 1
                t, ll[m] = fio.run_cmds(cmds, x=ll[m], ems=m)
                if t is not None:
                    pees[m] = t
            if pees[m].poll() is None:
                running = True
        for m in fio.nmini:
            if pees[m] is None:
                continue
            print "Open STDOUT"
            out[m] = open(fifo[m], 'w', 0)
            print '.'
            out[m].write(pees[m].stdout.read(1))
            print '.'
            pees[m].stdout.flush()
            print '.'
            out[m].close()

        print cnt, '-------------------'
        cnt += 1
    for m in fio.nmini:
        out[m] = open(fifo[m], 'w', 0)
        out[m].write(pees[m].stdout.read())
        pees[m].stdout.flush()
        out[m].close()
        print "Open STDERR"
        with open(fifo[m], 'w', 0) as out[m]:
            print '.'
            out[m].write(pees[m].stderr.read())
            print '.'
            pees[m].stderr.flush()
            print '.'
        print "Done"

    # END DEBUG

    fio.merge(fio.resolved.keys())

    yn = raw_input("Merge all mini files to A: (y/n) ")
    if yn == 'y':
        fio.unite()

    fio.write_cfg()

    yn = raw_input("Kill xterms: (y/n ) ")
    if yn == 'y':
        for k in xterms.keys():
            xterms[k].kill()

    yn = raw_input("Calc stats: (y/n ) ")
    if yn == 'y':
        s = 0
        for m in fio.nmini:
            tot = 0
            mmin = sys.maxsize
            mmax = 0
            for dataloggerlog in (
                    '125atoph5.log', '130toph5.log', 'segdtoph5.log'):
                if not os.path.exists(os.path.join(
                        fio.home, m, dataloggerlog)):
                    continue
                with open(os.path.join(fio.home, m, dataloggerlog)) as fh:
                    while True:
                        line = fh.readline()
                        if not line:
                            break
                        line = line.strip()
                        mo = processRE.match(line)
                        if mo:
                            flds = mo.groups()
                            tdoy = timedoy.TimeDOY(int(flds[0]),
                                                   int(flds[1]),
                                                   int(flds[2]),
                                                   int(flds[3]),
                                                   int(flds[4]),
                                                   int(flds[5]))
                            sz = os.path.getsize(flds[6])
                            tot += sz
                            if tdoy.epoch() < mmin:
                                mmin = tdoy.epoch()
                            if tdoy.epoch() > mmax:
                                mmax = tdoy.epoch()

                        elif doneRE.match(line):
                            flds = doneRE.match(line).groups()
                            tdoy = timedoy.TimeDOY(int(flds[0]),
                                                   int(flds[1]),
                                                   int(flds[2]),
                                                   int(flds[3]),
                                                   int(flds[4]),
                                                   int(flds[5]))

                            if tdoy.epoch() < mmin:
                                mmin = tdoy.epoch()
                            if tdoy.epoch() > mmax:
                                mmax = tdoy.epoch()
                            rate = (tot / (mmax - mmin)) / 1024. / 1024.
                            s += rate
                            print fh.name, line
                            print "===>", rate, "MB/second"
                            tot = 0
                            mmin = sys.maxsize
                            mmax = 0

        print "n: ", len(fio.nmini), "Ave: ", s / float(len(fio.nmini)),\
            "Total: ", s
