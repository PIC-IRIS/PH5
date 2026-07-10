#!/usr/bin/env pnpython3
#
# Update a ph5 file from a kef file
#
# Steve Azevedo, January 2007
#

import argparse
import logging
import os
import os.path
import time
from ph5.core import experiment, kefx, columns

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

# Force time zone to UTC
os.environ['TZ'] = 'UTC'
time.tzset()


class Rows_Keys(object):
    __slots__ = ('rows', 'keys')

    def __init__(self, rows=None, keys=None):
        self.rows = rows
        self.keys = keys

    def set(self, rows=None, keys=None):
        if rows is not None:
            self.rows = rows
        if keys is not None:
            self.keys = keys


def get_args():
    global KEFFILE, PH5, PATH, TRACE, MINIFILE

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("kef2ph5 --kef kef_file --nickname ph5_file_prefix "
                    "[--path path]")

    parser.description = ("Update a ph5 file from a kef file.\n\nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="outfile",
                        help="The ph5 file prefix (experiment nickname).",
                        required=True)
    parser.add_argument("-k", "--kef", dest="keffile",
                        help="Kitchen Exchange Format file.", required=True)
    parser.add_argument("-p", "--path", dest="path",
                        help="Path to directory where ph5 files are stored.",
                        default=".")
    parser.add_argument("-c", "--check", action="store_true", default=False,
                        dest="check",
                        help="Show what will be done but don't do it!")

    parser.add_argument("-m", "--miniPH5_xxxxx", dest="minifile",
                        metavar='n', default=0,
                        help="Go with das kef file to add das table to"
                             "a specific mini file.")

    args = parser.parse_args()

    KEFFILE = args.keffile
    PH5 = args.outfile
    PATH = args.path
    TRACE = args.check
    MINIFILE = args.minifile


def initializeExperiment():
    global EX, PH5, PATH

    EX = experiment.ExperimentGroup(nickname=PH5, currentpath=PATH)
    EDIT = True
    EX.ph5open(EDIT)
    EX.initgroup()


def openPH5(filename):
    '''   Open PH5 file, miniPH5_xxxxx.ph5   '''
    exrec = experiment.ExperimentGroup(nickname=filename)
    exrec.ph5open(True)
    exrec.initgroup()
    return exrec


def update_external_references():
    '''   Update external references in master.ph5 to
          miniPH5 files in Receivers_g    '''
    global INDEX_T_DAS
    LOGGER.info("Updating external references...")
    n = 0
    for i in INDEX_T_DAS.rows:
        external_file = i['external_file_name_s'][2:]
        external_path = i['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]

        #   Nuke old node
        try:
            group_node = EX.ph5.get_node(external_path)
            group_node.remove()
        except Exception as e:
            pass

        #   Re-create node
        try:
            EX.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            n += 1
        except Exception as e:
            # pass
            LOGGER.error("{0}\n".format(e.message))

    LOGGER.info("done, {0} das nodes recreated.\n".format(n))


def add_references(rs, EXREC=None):
    '''   Add a reference for each Das_t so we can look it up later   '''
    import string
    global EX
    for r in rs:
        flds = string.split(r, '/')
        das = string.split(flds[3], '_')[2]
        if EXREC is not None:
            g, das_t, receiver_t, time_t = EXREC.ph5_g_receivers.newdas(
                str(das))
            EXREC.ph5_g_maps.newdas('Das_g_', str(das))
        else:
            g = EX.ph5_g_receivers.getdas_g(das)
        EX.ph5_g_receivers.setcurrent(g)
        # Set reference
        columns.add_reference(r, EX.ph5_g_receivers.current_t_das)


def populateTables():
    global EX, KEFFILE, TRACE, MINIFILE, INDEX_T_DAS
    LOGGER.info("Loading {0} into {1}.".format(KEFFILE, PH5))
    k = kefx.Kef(KEFFILE)
    k.open()

    while True:
        n = k.read(10000)

        if n == 0:
            err = "Empty kef file."
            break

        EXREC = None

        if MINIFILE != 0:
            EXREC = openPH5('miniPH5_{0:05d}'.format(int(MINIFILE)))

        # Get Das_g references
        ret = k.strip_receiver_g()

        if ret:
            add_references(ret, EXREC)

        # Make sure Array_t_xxx, Event_t_xxx, and Offset_t_aaa_sss exist
        arrays, events, offsets, dass = k.strip_a_e_o_d()

        if arrays:
            for a in arrays:
                a = a.split(':')[0]
                EX.ph5_g_sorts.newArraySort(a)

        if events:
            for e in events:
                e = e.split(':')[0]
                EX.ph5_g_sorts.newEventSort(e)

        if offsets:
            for o in offsets:
                o = o.split(':')[0]
                EX.ph5_g_sorts.newOffsetSort(o)
        if dass:
            if MINIFILE == 0:
                LOGGER.error('Require MINIFILE for Das table!!!')
            else:
                rows, keys = EX.ph5_g_receivers.read_index()
                INDEX_T_DAS = Rows_Keys(rows, keys)
                k.dass_update(EXREC)
        else:
            if TRACE is True:
                err = k.batch_update(trace=True)
            else:
                err = k.batch_update()
    if dass:
        update_external_references()
        EXREC.ph5close()
    k.close()
    if err is True:
        LOGGER.error("There were errors! See output.")


def closePH5():
    global EX
    EX.ph5close()


def update_log():
    '''   Write a log of kef2ph5 activities.   '''
    global PH5, KEFFILE, PATH, TRACE
    # Don't log when run with the -c option
    if TRACE is True:
        return

    keffile = KEFFILE
    ph5file = os.path.join(PATH, PH5)
    klog = os.path.join(PATH, "kef2ph5.log")

    kef_mtime = time.ctime(os.stat(keffile).st_mtime)
    now = time.ctime(time.time())

    line = "%s*:*%s*:*%s*:*%s\n" % (now, ph5file, keffile, kef_mtime)
    if not os.path.exists(klog):
        line = "modification_time*:*experiment_nickname*:*\
        kef_filename*:*kef_file_mod_time\n" + \
               "-------------------------------------------------------------\
               -------------\n" + line

    try:
        LOGGER.info("Updated kef2ph5.log file.")
        fh = open(klog, 'a+')
        fh.write(line)
        fh.close()
    except BaseException:
        LOGGER.warning("Failed to write kef2ph5.log file.")


def main():
    get_args()
    initializeExperiment()
    populateTables()
    closePH5()
    update_log()


if __name__ == '__main__':
    main()
