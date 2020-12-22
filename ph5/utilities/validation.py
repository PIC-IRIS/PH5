"""
common functions for validation
"""
import tables


def addLog(errmsg, unique_errors, logger=None, logType='error'):
    unique_errors.add((errmsg, logType))
    if logger is not None:
        if logType == 'error':
            logger.error(errmsg)
        if logType == 'warning':
            logger.warning(errmsg)


def check_resp_data(ph5table, path, header, checked_data_files):
    """
    Check if response data is loaded for the response filename
    :para ph5table: table ph5
    :para name: response filename
    :para errors: list of errors
    :param logger: logger of the caller
    :return: True if node
             False if node not exist
    """
    if path == '':
        return

    name = path.split('/')[-1]
    if name in checked_data_files.keys():
        if checked_data_files[name] != '':
            raise Exception(checked_data_files[name])
        else:
            return

    checked_data_files[name] = ''
    try:
        ph5table.get_node(ph5table.root.Experiment_g.Responses_g, name)
    except tables.NoSuchNodeError:
        errmsg = "%sNo response data loaded for %s." % (header, name)
        checked_data_files[name] = errmsg
        raise Exception(errmsg)
    return


def check_resp_file_name(Response_t, info, header, ftype,
                         errors, logger, m_file=None):
    """
    Check response file name in response_t matches with info from station entry
    :param Response_t: response entry according to info[n_i]
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ftype: one of the strings: das/sensor/metadata
    :para errors: list of errors
    :param logger: logger of the caller
    :return:
      respname, resppath if info and response's path match
      if info and response's path not match:
        if ftype=metadata: return respname, None to have the name in metadata
            format for the error message later if needed
        else: return None
    """
    info['dmodel'] = info['dmodel'].translate(None, ',-=._ ')
    info['smodel'] = info['smodel'].translate(None, ',-=._ ')
    if ftype == 'metadata':
        std_info_fname = "%(dmodel)s_%(smodel)s_%(spr)s%(cha_code)s" % info
        info_fname = std_info_fname.replace('_', '').lower()
    elif ftype == 'sensor':
        std_info_fname = info['smodel']
        info_fname = std_info_fname.lower()
    elif ftype == 'das':
        info['gain'] = Response_t['gain/value_i']
        std_info_fname = "%(dmodel)s_%(spr)s_%(sprm)s_%(gain)s" % info
        info_fname = std_info_fname.replace('_', '').lower()

    file_field = 'response_file_das_a'
    if ftype == 'sensor':
        file_field = 'response_file_sensor_a'
    std_response_fname = Response_t[file_field].split('/')[-1]
    response_fname = std_response_fname.replace('_', '').lower()

    if info_fname == response_fname:
        return True, std_info_fname

    if response_fname == '':
        if ftype == 'sensor':
            # for das and metadata, blank info_fname will return False
            # in check_response_info
            errmsg = ("%sresponse_file_sensor_a is blank while %s model "
                      "exists." % (header, ftype))
            addLog(errmsg, errors, logger, logType='warning')
        return False, None
    else:
        if ftype == 'metadata':
            # return std_info_fname to continue checking
            return False, std_info_fname
        info['m_file'] = ''
        if (ftype == 'das' and info['smodel'] != '' and
                Response_t['response_file_sensor_a'] == ''):
            info['m_file'] = " or '%s'" % m_file
        if ftype == 'das':
            models = ''
            if m_file is not None:
                models += "'%(smodel)s' and "
            models += "'%(dmodel)s'; sr=%(spr)s srm=%(sprm)s gain=%(gain)s"
            if m_file is not None:
                models += " 'cha=%(cha_code)s'"
        if ftype == 'sensor':
            models = "%(smodel)s"
        errmsg = ("{0}response_file_{1}_a '{2}' is inconsistence with model(s)"
                  " {3}.").format(header,
                                  ftype,
                                  std_response_fname,
                                  models % info)
        addLog(errmsg, errors, logger, logType='warning')
        return False, None


def check_response_info(info, ph5, checked_data_files, errors, logger):
    """
    Check in response info for each station entry if the response filenames are
    correct (das filename created by metadata or das/sensor filename
    created by resp_load) and the response data are loaded.
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ph5: ph5 object
    :param checked_data_files: set of resp filenames that check_resp_data() has
        run for it
    :param errors: list of errors
    :param logger: logger of the caller
    :return:
        False if no response data loaded
        (d_path, s_path) in which d_path and s_path are response paths for
            das or sensor if loaded or None if none is loaded
    """
    Response_t = ph5.get_response_t_by_n_i(info['n_i'])
    header = ("array {0}, station {1}, channel {2}, "
              "response_table_n_i {3}: ").format(info['array'],
                                                 info['sta'],
                                                 info['cha_id'],
                                                 info['n_i'])
    if Response_t is None:
        errmsg = ("%sresponse_t has no entry for n_i=%s"
                  % (header, info['n_i']))
        return False, errmsg
    if info['n_i'] == -1:
        # metadata no response signal
        errmsg = ("%sMetadata response with n_i=-1 has no response data."
                  % header)
        return False, errmsg

    d_file = None
    s_file = ''
    # check resp file from metadata
    ret, d_file = check_resp_file_name(
        Response_t, info, header, 'metadata', errors, logger)
    if not ret:
        # check sensor
        ret, s_file = check_resp_file_name(
            Response_t, info, header, 'sensor', errors, logger)

        # check das
        check_resp_file_name(
            Response_t, info, header, 'das', errors, logger, d_file)

    das_resp_path = Response_t['response_file_das_a']
    sens_resp_path = Response_t['response_file_sensor_a']
    try:
        if das_resp_path == '':
            errmsg = "%sresponse_file_das_a is blank." % header
            return False, errmsg
        check_resp_data(ph5.ph5, das_resp_path, header, checked_data_files)
        if s_file is not None:
            check_resp_data(ph5.ph5, sens_resp_path, header,
                            checked_data_files)
    except Exception as e:
        return False, str(e)
    return das_resp_path, sens_resp_path


def check_resp_unique_n_i(ph5, errors, logger=None):
    # check for duplicated n_i in response table
    n_i_list = [e['n_i'] for e in ph5.Response_t['rows']]
    dup_indexes = set([i for i in n_i_list
                       if n_i_list.count(i) > 1])
    if len(dup_indexes) != 0:
        errmsg = "Response_t n_i(s) duplicated: %s" % \
                 ','.join(map(str, dup_indexes))
        addLog(errmsg, errors, logger)


def check_resp_load(response_t, errors, logger):
    # check if resp_load already run for the ph5
    for entry in response_t['rows']:
        if entry['response_file_das_a'] != '':
            return True
    errmsg = ("All response file names are blank in response "
              "table. Check if resp_load has been run.")
    addLog(errmsg, errors, logger)
    return errmsg


def check_lat_lon_elev(station):
    errors = []
    warnings = []
    if station['location/X/value_d'] == 0:
        warnings.append("Channel longitude seems to be 0. Is this correct???")
    if not -180 <= float(station['location/X/value_d']) <= 180:
        errors.append("Channel longitude %s not in range [-180,180]"
                      % station['location/X/value_d'])
    if station['location/X/units_s'] in [None, '']:
        warnings.append("No Station location/X/units_s value found.")

    if station['location/Y/value_d'] == 0:
        warnings.append("Channel latitude seems to be 0. Is this correct???")
    if not -90 <= float(station['location/Y/value_d']) <= 90:
        errors.append("Channel latitude %s not in range [-90,90]"
                      % station['location/Y/value_d'])
    if station['location/Y/units_s'] in [None, '']:
        warnings.append("No Station location/Y/units_s value found.")

    if station['location/Z/value_d'] == 0:
        warnings.append("Channel elevation seems to be 0. Is this correct???")
    if station['location/Z/units_s'] in [None, '']:
        warnings.append("No Station location/Z/units_s value found.")
    return errors, warnings
