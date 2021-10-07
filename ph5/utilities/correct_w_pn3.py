#
# Lan Dam, September 2021
#


import argparse
import os
import sys
import logging
import tables
from shutil import copy
import time

from ph5.core import (ph5api, experiment, columns, experiment_pn3, ph5api_pn3,
                      timedoy)
from ph5.utilities import nuke_table, kef2ph5 as K2T, tabletokef as T2K
from ph5 import LOGGING_FORMAT
import tabletokef as T2K

PROG_VERSION = "2021.271"
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("correctwpn3 --pn4 pn4path --pn3 pn3path")

    parser.description = ("Recreate Array_t with info from pn3.\n"
                          "Exclude entries that don't match with index_t, das_t.\n"
                          "Remove external links and all pn4's minifiles.\n"
                          "Copy pn3's minifiles to pn4.\n"
                          "Create new external link based on info from Index_t. \n"
                          "Version: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("--pn4", dest="pn4path",
                        help="Path to pn4 master file (not include master.ph5)",
                        metavar="pn4path", required=True)

    parser.add_argument("--pn3", dest="pn3path",
                        help="Path to pn3 master file (not include master.ph5)",
                        metavar="pn3path", required=True)

    parser.add_argument("-a", "--add_info", dest="addInfoFile",
                        help=("Path to file containing user's values for "
                              "array_t (include filename)\n"
                              "Format for each line: key=value\n"
                              "Ex:\n"
                              "\tsensor/model_s=L28\n"
                              "\tsensor/manufacturer_s=Sercel"),
                        metavar="addInfoFile")
    parser.add_argument("-s", dest="skip_missing_minifile",
                        help="Flag to skip reporting about minifile",
                        action='store_true', default=True)

    args = parser.parse_args()
    skip_missing_minifile = args.skip_missing_minifile
    pn4path = args.pn4path
    pn3path = args.pn3path
    addInfoFile = args.addInfoFile
    return pn4path, pn3path, addInfoFile, skip_missing_minifile


def set_logger():
    """
    Setting logger's format and filehandler
    """

    # set filehandler
    ch = logging.FileHandler("correct_w_pn3.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def getDupOfField(listOfDict, mainK1, mainK2, dupK):
    """
    return list of (mainK1, mainK2) that have dupK duplicated
    """
    c = {}
    for d in listOfDict:
        c.setdefault((d[mainK1], d[mainK2]), []).append(d[dupK])
    b = [{'mixK': k, dupK: v} for k, v in c.iteritems()]
    d = [e['mixK'] for e in b if len(e[dupK]) > 1]
    return d

# ########################### CHECK ISSUES ##############################
def get_array_t(pn3object):
    """
    + read array_t from pn3
    + remove entry with deploy_t=pickup_time
    + return list of entry with array_name to identify array
    """
    entryList = []
    sameDepPic = {}
    pn3object.read_array_t_names()
    count = 0
    remCount = 0
    dasDict = {}
    for aname in sorted(pn3object.Array_t_names):
        pn3object.read_array_t(aname)
        arraybyid = pn3object.Array_t[aname]['byid']
        arrayorder = pn3object.Array_t[aname]['order']

        for ph5_station in arrayorder:
            station_list = arraybyid.get(ph5_station)
            for deployment in station_list:
                station_len = len(station_list[deployment])
                for st_num in range(0, station_len):
                    e = station_list[deployment][st_num]
                    if e['deploy_time/ascii_s'] == e['pickup_time/ascii_s']:
                        if e['deploy_time/ascii_s'] not in sameDepPic.keys():
                            sameDepPic[e['deploy_time/ascii_s']] = {}
                        if e['das/serial_number_s'] not in sameDepPic[e['deploy_time/ascii_s']]:
                            sameDepPic[e['deploy_time/ascii_s']][e['das/serial_number_s']] = 0
                        sameDepPic[e['deploy_time/ascii_s']][e['das/serial_number_s']] += 1
                        remCount += 1
                    else:
                        e['array_name'] = aname
                        entryList.append(e)
                        if e['das/serial_number_s'] not in dasDict.keys():
                            dasDict[e['das/serial_number_s']] = []
                        dasDict[e['das/serial_number_s']].append(e)
                    count += 1
    cormdas = []
    for t in sameDepPic.keys():
        for das in sameDepPic[t].keys():
            remNo = sameDepPic[t][das]
            total = sameDepPic[t][das]
            if das in dasDict:
                total += len(dasDict[das])
            sameDepPic[t][das] = "%s/%s" % (remNo, total)
            if total == 4:
                cormdas.append(das)

    if sameDepPic != {}:
        msg = ("Due to coincided deploy and pickup times, %s/%s  entries will be removed from array_t:\n"
               "[time]: {[das_serial]: [rem/total], [das_serial]: [rem/total], ...},\n" % (remCount, count))
        for deptime, dasncount in sameDepPic.items():
            msg += "%s: %s\n" % (deptime, dasncount)
        LOGGER.warning(msg)

    for d in dasDict:
        res = getDupOfField(dasDict[d], 'array_name', 'channel_number_i', 'deploy_time/ascii_s')
        for r in res:
            array, channel = r
            LOGGER.warning('Das %s channel %s duplicated in %s. User need to handle this manually'
                           % (d, channel, array))

    return entryList, dasDict.keys()


def get_index_t(pn3object, pn3_array_t, das_of_array_t):
    """
    + read index_t from pn3object
    + remove entries that have mismatch das
    + return new pn3_array_t, pn3_index_t
    """
    pn3object.read_index_t()
    pn3_index_t = []
    index_t_remDas = []     # list of das to be removed from index_t
    totalOrgIndexE = len(pn3object.Index_t['rows'])
    for e in pn3object.Index_t['rows']:
        if e['serial_number_s'] not in das_of_array_t:
            index_t_remDas.append(e['serial_number_s'])
        else:
            pn3_index_t.append(e)

    if index_t_remDas != []:
        msg = "Due to nonexistency in array_t %s/%s das will be removed " \
              "from index_t:\n%s"
        LOGGER.warning(msg % (len(index_t_remDas), totalOrgIndexE,
                              sorted(index_t_remDas)))

    array_t_remDas = {}     # dict of das to be removed from each array_t
    totalOrgArrayE = len(pn3_array_t)
    das_of_index_t = [e['serial_number_s'] for e in pn3_index_t]
    new_pn3_array_t = []
    for e in pn3_array_t:
        if e['das/serial_number_s'] not in das_of_index_t:
            if e['array_name'] not in array_t_remDas:
                array_t_remDas[e['array_name']] = []
            array_t_remDas[e['array_name']].append(e['das/serial_number_s'])
        else:
            new_pn3_array_t.append(e)

    if array_t_remDas != {}:
        msg = ("Due to nonexistency in index_t %s/%s das will be removed"
               " from array_t:\n"
               % (len(array_t_remDas), totalOrgArrayE))
        for a, e in array_t_remDas.items():
            msg += "%s: %s\n" % (a, e)
        LOGGER.warning(msg)

    return pn3_index_t, new_pn3_array_t


def get_das_t(pn3object, pn3_array_t, pn3_index_t):
    """
    + read das_g from pn3
    + compare das with filtered pn3_index_t and remove ones that are mismatch
    + build pn3_das_t for the ones that's in existing minifile
    """
    pn3object.read_das_g_names()
    all_das_g_name = pn3object.Das_g_names
    # print("all_das_g_name: ", all_das_g_name)
    all_das = [name.replace("Das_g_", "") for name in all_das_g_name.keys()]
    # print(all_das)
    #
    index_t_das = [e['serial_number_s'] for e in pn3_index_t]
    in_das_no_index = [d for d in all_das if d not in index_t_das]
    if in_das_no_index != []:
        msg = ("Compare Das_g against the filtered list of index_t and "
               "array_t, the following Das will be removed from Das data:\n"
               " %s" % sorted(in_das_no_index))
        LOGGER.warning(msg)
        all_das = [d for d in all_das if d in index_t_das]

    in_index_no_das = [d for d in index_t_das if d not in all_das]
    if in_index_no_das != []:
        msg = ("Compare filtered list of index_t and array_t agains Das_g, "
               "the following Das's entries in array_t and index_t will be "
               "removed:\n %s" % sorted(in_index_no_das))
        LOGGER.warning(msg)
        pn3_array_t = [e for e in pn3_array_t if e['das/serial_number_s'] in all_das]
        pn3_index_t = [e for e in pn3_index_t if e['serial_number_s'] in all_das]

    # print(all_das_g_name['Das_g_11736']._v_pathname)
    pn3dir = os.path.join(os.getcwd(), pn3object.currentpath)
    # p = all_das_g_name['Das_g_11736']._get_filename_node()[0]

    existing_minifile_dict = {}
    missing_minifiles = set()
    empty_das_t_list = []
    pn3_das_t = {}

    for das_g_name in all_das_g_name.keys():
        das = das_g_name.replace("Das_g_", "")
        das_g = all_das_g_name[das_g_name]
        minifile = das_g._get_filename_node()[0]
        minifile_fullpath = os.path.join(pn3dir, minifile)
        if not os.path.isfile(minifile_fullpath):
            missing_minifiles.add(minifile)
            continue
        else:
            if minifile not in existing_minifile_dict:
                existing_minifile_dict[minifile] = []
            existing_minifile_dict[minifile].append(das)
        das = das_g_name.replace("Das_g_", "")
        pn3object.read_das_t(das)
        if pn3object.Das_t[das]['rows'] == []:
            empty_das_t_list.append(das)
        pn3_das_t[das] = pn3object.Das_t[das]['rows']
    if empty_das_t_list != []:
        msg = "The following Das have empty das_t: %s" % empty_das_t_list
        LOGGER.warning(msg)

    if missing_minifiles != []:
        msg = "The following minifiles are missing:\n%s" % missing_minifiles
        LOGGER.warning(msg)

    return (pn3_das_t, pn3_index_t, pn3_array_t,
            in_das_no_index, existing_minifile_dict)


def check_pn3_issues(pn3object):
    """
    compare between array_t, index_t, das_t, remove mismatch das,
    remove station with deploy=pickup
    """
    pn3_array_t, das_of_array_t = get_array_t(pn3object)
    pn3_index_t, pn3_array_t = get_index_t(
        pn3object, pn3_array_t, das_of_array_t)
    return get_das_t(pn3object, pn3_array_t, pn3_index_t)
# ######################### END CHECK ISSUES ############################


def create_index_t_backup(pn3object, path):
    """
        create index_t backup in pn4path
    """
    T2K.init_local()
    T2K.EX = pn3object
    T2K.read_index_table()
    tdoy = timedoy.TimeDOY(epoch=time.time())
    tt = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)
    prefix = "{0}_{1}".format('Index_t', tt)
    outfile = "{0}_00.kef".format(prefix)
    # Do not overwite existing file
    i = 1
    while os.path.exists(outfile):
        outfile = "{0}_{1:02d}.kef".format(prefix, i)
        i += 1
    # Exit if we can't write backup kef
    if os.access(os.getcwd(), os.W_OK):
        LOGGER.info("Writing table backup: {0}."
                    .format(os.path.join(os.getcwd(), outfile)))
    else:
        LOGGER.error(
            "Can't write: {0}.\nExiting!"
            .format(os.path.join(os.getcwd(), outfile)))
        sys.exit(-3)
    try:
        fh = open(os.path.join(path, outfile), 'w')
        fh.write("# Created by correctwpn3 from pn3's index_t to recover "
                 "removed das")
        T2K.table_print('/Experiment_g/Receivers_g/Index_t', T2K.INDEX_T,
                        fh=fh)
        fh.close()
    except Exception as e:
        LOGGER.error(
            "Failed to save {0}.\n{1}\nExiting!"
            .format(os.path.join(os.getcwd(), outfile), e.message))
        sys.exit(-4)
    return outfile


# ########################### CLEAN UP PN4 #############################
def cleanup_pn4(pn4object):
    """
    + truncate array_t, index_t
    + remove ext_link for das_g
    """
    ret = raw_input("\n=========================================\n"
                    "All external links to minifiles are going to "
                    "be removed from : %s.\n"
                    "Do you want to continue?(y/n)" % pn4object.filename)
    if ret == 'n':
        return False
    ##### REMOVE Array_t #####
    pn4object.read_array_t_names()
    rem_arrays = []
    failed_rem_arrays = []
    for aname in sorted(pn4object.Array_t_names):
        ARRAY_TABLE = int(aname[-3:])
        if pn4object.ph5_g_sorts.nuke_array_t(ARRAY_TABLE):
            rem_arrays.append(aname)
        else:
            failed_rem_arrays.append(aname)
    LOGGER.info("Remove from pn4 object %s" % rem_arrays)

    ##### REMOVE INDEX_T #####
    pn4object.ph5_g_receivers.nuke_index_t()
    LOGGER.info("Remove Index_t from pn4 object")

    #### REMOVE EXT_LINK FOR Das_g ####
    pn4object.read_das_g_names()
    all_das_g_name = pn4object.Das_g_names
    rem_das = []
    for das_g_name in all_das_g_name.keys():
        external_path = all_das_g_name[das_g_name]._v_pathname
        try:
            group_node = pn4object.ph5.get_node(external_path)
            group_node.remove()
            rem_das.append(external_path.split('/')[3].replace("Das_g_", ""))
        except Exception as e:
            pass
    LOGGER.info("Remove Das_g external links from pn4 object%s" % rem_das)
    return pn4object
# ########################## END CLEAN UP PN4 ###########################


# ############################ RECREATE PN4 #############################
def get_band_code(sample_rate):
    if sample_rate >= 1000:
        band_code = 'G'
    elif sample_rate >= 250 and sample_rate < 1000:
        band_code = 'D'
    elif sample_rate >= 80 and sample_rate < 250:
        band_code = 'E'
    elif sample_rate >= 10 and sample_rate < 80:
        band_code = 'S'
    else:
        band_code = 'X'
    return band_code

def convert_to_pn4_array(entry, pn3_das_t, addInfo, skip_missing_minifile):
    """
    param pn3e: array entry form pn3
    param addInfoFile
    """
    del entry['array_name']
    das = entry['das/serial_number_s']
    chan = entry['channel_number_i']
    dep = entry['deploy_time/epoch_l']
    pic = entry['pickup_time/epoch_l']
    if das in pn3_das_t.keys():
        rel_das_chan_rows = [e for e in pn3_das_t[das]
                             if e['channel_number_i'] == chan]
        if rel_das_chan_rows == []:
            LOGGER.error("Cannot fill in station's sample_rate_i, "
                         "seed_band_code_s and receiver_table_n_i because "
                         "chan %s doen't exist for %s in das_t "
                         % (chan, das))
        else:
            rel_das_time_rows = [e for e in rel_das_chan_rows
                                 if dep <= e ['time/epoch_l'] <= pic]
            sample_rates = list({e['sample_rate_i']
                                 for e in rel_das_time_rows})
            if len(sample_rates) > 1:
                msg = ("There are more than one sample rate for das %s at "
                       "channel %s. User need to correct sample rate in "
                       "array_t by themselves." % (das, chan))
                LOGGER.warning(msg)
            entry['sample_rate_i'] = sample_rates[0]
            entry['seed_band_code_s'] = get_band_code(sample_rates[0])
            entry['receiver_table_n_i'] = rel_das_time_rows[0][
                'receiver_table_n_i']
    else:
        if not skip_missing_minifile:
            LOGGER.error("Cannot fill in station's sample_rate_i, "
                         "seed_band_code_s and receiver_table_n_i because das "
                         "%s belongs to a missing minifile." % das)

    entry['sample_rate_multiplier_i'] = 1
    entry['seed_instrument_code_s'] = 'P'
    entry['seed_orientation_code_s'] = 'Z'
    entry['seed_station_name_s'] = entry['id_s']

    for k in addInfo:
        if k in entry.keys():
            entry[k] = addInfo[k]

    return entry


def recreate_array_t(pn4object, pn3_array_t, pn3_das_t, addInfo,
                     skip_missing_minifile):
    pn3_array_dict = {}
    for e in pn3_array_t:
        if e['array_name'] not in pn3_array_dict.keys():
            pn3_array_dict[e['array_name']] = []
        pn3_array_dict[e['array_name']].append(e)
    for array_name in pn3_array_dict.keys():
        a = pn4object.ph5_g_sorts.newArraySort(array_name)
        for e in pn3_array_dict[array_name]:
            e = convert_to_pn4_array(e, pn3_das_t, addInfo,
                                     skip_missing_minifile)
            try:
                columns.populate(a, e)
            except Exception as err:
                LOGGER.error(err.message)


def recreate_index_t(pn4object, pn3_index_t):
    for e in pn3_index_t:
        pn4object.ph5_g_receivers.populateIndex_t(e)


def prepare_minifiles(pn4path, pn3path, pn3_das_t, existing_minifiles):
    ret = raw_input("\n=========================================\n"
                    "All minifiles are going to be deleted in %s.\n"
                    "Do you want to continue?(y/n)" % pn4path)
    if ret == 'n':
        return False

    for f in existing_minifiles:
        minipn3path = os.path.join(pn3path, f)
        minipn4path = os.path.join(pn4path, f)
        copy(minipn3path, minipn4path)
        miniobj = ph5api.PH5(path=pn4path, nickname=f, editmode=True)
        miniobj.read_das_g_names()
        all_das_g_name = miniobj.Das_g_names
        for group in all_das_g_name:
            das = group.replace("Das_g_", "")
            groupnode = miniobj.ph5_g_receivers.getdas_g(das)
            # if das not in pn3_das_t.keys():
            #     # group_node = miniobj.ph5.get_node(group)
            #     groupnode.remove()
            # else:
            # remove das_t
            das_t = miniobj.ph5_g_receivers.ph5.get_node(
                '/Experiment_g/Receivers_g/Das_g_%s' % das,
                name='Das_t',
                classname='Table')
            das_t.remove()
            # initialize das_t with pn4 format
            experiment.initialize_table(
                miniobj.ph5_g_receivers.ph5,
                '/Experiment_g/Receivers_g/Das_g_%s' % das,
                'Das_t',
                columns.Data, expectedrows=1000)
            miniobj.ph5_g_receivers.setcurrent(groupnode)
            for e in pn3_das_t[das]:
                # add new das_t information with sample_rate_multiplier_i=1
                e['sample_rate_multiplier_i'] = 1
                miniobj.ph5_g_receivers.populateDas_t(e)
        miniobj.close()
    return True


def create_external_links(pn4object, pn3_index_t, rem_das,
                          existing_minifile_dict):
    for entry in pn3_index_t:
        das = entry['serial_number_s']
        external_file = entry['external_file_name_s'][2:]
        external_path = entry['hdf5_path_s']
        target = external_file + ':' + external_path
        external_group = external_path.split('/')[3]
        try:
            pn4object.ph5.create_external_link(
                '/Experiment_g/Receivers_g', external_group, target)
            LOGGER.info("External link '%s' is created." % target)
        except Exception as e:
            # pass
            LOGGER.error("{0}\n".format(e.message))

    das_in_existing_mini = []
    for das_list in existing_minifile_dict.values():
        das_in_existing_mini += das_list
    for das in rem_das:
        if das in das_in_existing_mini:
            LOGGER.info("External link is not created for das %s. "
                        "Use tool 'create_ext' when metadata is found." % das)
    
    
# ########################## END RECREATE PN4 ###########################

def getAddInfo(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
        addInfo = {}
        for line in lines:
            ss = [s.strip() for s in line.split('=')]
            if len(ss) != 2:
                raise Exception("The format of addInfo file is incorrect. "
                                "It should be fieldname=value for each line.")
            addInfo[ss[0]] = ss[1]
            if ss[0][-1] == 'i':
                addInfo[ss[0]] = int(addInfo[ss[0]])
            elif ss[0][-1] == 'd':
                addInfo[ss[0]] = float(addInfo[ss[0]])
        return addInfo


def main():
    pn4path, pn3path, addInfoFile, skip_missing_minifile = get_args()
    addInfo = []
    if addInfoFile is not None:
        addInfo = getAddInfo(addInfoFile)

    set_logger()
    pn3object = ph5api_pn3.PH5(
        path=pn3path, nickname='master.ph5', editmode=False)
    (pn3_das_t,
     pn3_index_t,
     pn3_array_t,
     rem_das,
     existing_minifile_dict) = check_pn3_issues(pn3object)
    create_index_t_backup(pn3object, pn4path)
    pn3object.close()

    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    pn4object = ph5api.PH5(path=pn4path, nickname='master.ph5', editmode=True)
    pn4object = cleanup_pn4(pn4object)
    if not pn4object:
        LOGGER.warning("The program was interupted by user 1.")
        sys.exit()
    recreate_array_t(pn4object, pn3_array_t, pn3_das_t, addInfo,
                     skip_missing_minifile)

    recreate_index_t(pn4object, pn3_index_t)
    ret = prepare_minifiles(
        pn4path, pn3path, pn3_das_t, existing_minifile_dict.keys())

    if not ret:
        LOGGER.warning("The program was interupted by user 2.")
        sys.exit()
    create_external_links(pn4object, pn3_index_t, rem_das,
                          existing_minifile_dict)
    pn4object.close()
    os.environ["HDF5_USE_FILE_LOCKING"] = "TRUE"


if __name__ == '__main__':
    main()