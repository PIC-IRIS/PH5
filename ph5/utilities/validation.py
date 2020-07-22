"""
common functions for validation
"""
import tables


def addError(errmsg, errors, logger):
    if errmsg not in errors:
        errors.append(errmsg)
    if logger:
        logger.error(errmsg)


def check_resp_data(ph5table, name, errors, logger):
    """
    Check if response data is loaded for the response filename
    :para ph5table: table ph5
    :para name: response filename
    :para errors: list of errors
    :param logger: logger of the caller
    :return: True if node
             False if node not exist
    """
    try:
        ph5table.get_node(ph5table.root.Experiment_g.Responses_g, name)
    except tables.NoSuchNodeError:
        errmsg = "No response data loaded for %s." % name
        addError(errmsg, errors, logger)
        return False
    return True


def check_resp_file_name(Response_t, info, ftype, unique_filenames_n_i,
                         errors, logger, m_file=None):
    """
    Check response file name in response_t matches with info from station entry
    :param Response_t: response entry according to info[n_i]
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ftype: one of the strings: das/sensor/metadata
    :param unique_filenames_n_i: list of tupples (resp filename, n_i) to help
        not check the info if already checked
    :para errors: list of errors
    :param logger: logger of the caller
    :return:
      respname, resppath if info and response's path match
      if info and response's path not match:
        if ftype=metadata: return respname, None to have the name in metadata
            format for the error message later if needed
        else: return None
    """
    info['dmodel'] = info['dmodel'].translate(
        None, ',-=.').replace(' ', '')
    info['smodel'] = info['smodel'].translate(
        None, ',-=.').replace(' ', '')
    if ftype == 'metadata':
        info_fname = "%(dmodel)s_%(smodel)s_%(spr)s%(cha_code)s" % info
    elif ftype == 'sensor':
        info_fname = info['smodel']
    elif ftype == 'das':
        info['gain'] = Response_t['gain/value_i']
        info_fname = "%(dmodel)s_%(spr)s_%(sprm)s_%(gain)s" % info

    file_field = 'response_file_das_a'
    if ftype == 'sensor':
        file_field = 'response_file_sensor_a'
    response_fname = Response_t[file_field].split('/')[-1]

    n_i = info['n_i']
    filename_n_i = (info_fname, n_i)
    if filename_n_i in unique_filenames_n_i:
        return info_fname, Response_t[file_field]

    if (response_fname == ''):
        if (info_fname != '' and ftype != 'metadata'):
            errmsg = ("{0}-{1}-{2} response_table_n_i {3}: "
                      "response_file_{4}_a is blank while {5} model "
                      "exists.").format(info['array'],
                                        info['sta'],
                                        info['cha_id'],
                                        info['n_i'],
                                        ftype,
                                        ftype)
            addError(errmsg, errors, logger)
        return None
    else:
        if info_fname != response_fname:
            if ftype == 'metadata':
                return info_fname, None
            info['m_file'] = ''
            if (ftype == 'das' and info['smodel'] != '' and
                    Response_t['response_file_sensor_a'] == ''):
                info['m_file'] = " or '%s'" % m_file
            errmsg = ("{0}-{1}-{2} response_table_n_i {3}: Response {4} "
                      "file name should be '{5}'{6} instead of '{7}'."
                      ).format(info['array'],
                               info['sta'],
                               info['cha_id'],
                               info['n_i'],
                               ftype,
                               info_fname,
                               info['m_file'],
                               response_fname)
            addError(errmsg, errors, logger)
            return None

    unique_filenames_n_i.append(filename_n_i)
    return info_fname, Response_t[file_field]


def check_response_info(info, ph5, unique_filenames_n_i, checked_data_files,
                        errors, logger):
    """
    Check in response info for each station entry if the response filenames are
    correct (das filename created by metadata or das/sensor filename
    created by resp_load) and the response data are loaded.
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ph5: ph5 object
    :param unique_filenames_n_i: list of tupples (resp filename, n_i) to help
        not check the info if already checked
    :param checked_data_files: diction of resp filename of which data have been
        check for being loaded
    :param errors: list of errors
    :param logger: logger of the caller
    :return:
        False if no response data loaded
        (d_path, s_path) in which d_path and s_path are response paths for
            das or sensor if loaded or None if none is loaded
    """
    Response_t = ph5.get_response_t_by_n_i(info['n_i'])
    if Response_t is None:
        errmsg = "No response entry for n_i=%s." % info['n_i']
        addError(errmsg, errors, logger)
        return False
    if info['n_i'] == -1:
        # metadata no response signal
        return False

    m_file = None
    # check resp file from metadata
    m_ret = check_resp_file_name(
        Response_t, info, 'metadata', unique_filenames_n_i, errors, logger)
    if m_ret is not None:
        m_file, m_path = m_ret
        if m_path is not None:
            # resp file is metadata type => don't need to check other types
            if m_file not in checked_data_files.keys():
                if check_resp_data(ph5.ph5, m_file, errors, logger):
                    checked_data_files[m_file] = True
                    return (m_path, None)
                else:
                    checked_data_files[m_file] = False
                    return False
            if checked_data_files[m_file]:
                return (m_path, None)
            else:
                return False

    # check sensor
    s_ret = check_resp_file_name(
        Response_t, info, 'sensor', unique_filenames_n_i, errors, logger)
    if s_ret is not None:
        s_file, s_path = s_ret
        if s_file not in checked_data_files.keys():
            if check_resp_data(ph5.ph5, s_file, errors, logger):
                checked_data_files[s_file] = True
            else:
                checked_data_files[s_file] = False
                s_path = None
        else:
            if not checked_data_files[s_file]:
                s_path = None
    else:
        s_file, s_path = None, None

    # check das
    ret = check_resp_file_name(
        Response_t, info, 'das', unique_filenames_n_i, errors, logger, m_file)
    if ret is not None:
        d_file, d_path = ret
        if d_file not in checked_data_files.keys():
            if check_resp_data(ph5.ph5, d_file, errors, logger):
                checked_data_files[d_file] = True
                return (d_path, s_path)
            else:
                checked_data_files[d_file] = False
                return (None, s_path)
        else:
            if checked_data_files[d_file]:
                return (d_path, s_path)
            else:
                return (None, s_path)
    else:
        return (None, s_path)


def check_resp_unique_n_i(ph5, errors, logger):
    # check for duplicated n_i in response table
    n_i_list = [e['n_i'] for e in ph5.Response_t['rows']]
    dup_indexes = set([i for i in n_i_list
                       if n_i_list.count(i) > 1])
    if len(dup_indexes) != 0:
        errmsg = "Response_t n_i(s) duplicated: %s" % \
                 ','.join(map(str, dup_indexes))
        addError(errmsg, errors, logger)
