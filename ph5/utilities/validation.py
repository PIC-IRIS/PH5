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


def check_resp_data(ph5table, path, header, checked_data_files, n_i):
    """
    Check if response data is loaded for the response filename
    :param ph5table: table ph5
    :param path: path filled in the response file name of response_t (str)
    :param header: string of array-station-channel to help users identify
            where the problem belong to (str)
    :param checked_data_files: set of resp filenames that check_response_info()
        has run for it
    :param n_i: response index
    :return: raise Exception if there is no response data
    """
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
        errmsg = "%sResponse_t[%s]:No response data loaded for %s." % \
                 (header, n_i, name)
        checked_data_files[name] = errmsg
        raise Exception(errmsg)
    return


def check_resp_file_name(Response_t, info, header, ftype, errors, logger):
    """
    Check response file name in response_t matches with info from station entry
    :param Response_t: response entry according to info[n_i]
    :param info: info needed from each station:
            dict {n_i, array, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :para header: string of array-station-channel to help user identify where
            the problem belong to (str)
    :param ftype: one of the strings: das/sensor/metadata
    :para errors: list of errors
    :param logger: logger of the caller
    :return: True: if pass all check
             False: if response filename not match with info
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
        return True

    if response_fname == '':
        if ftype == 'sensor':
            # for das and metadata, blank info_fname will return False
            # in check_response_info
            errmsg = ("%sResponse_t[%s]:response_file_sensor_a is blank while "
                      "%s model exists." % (header, info['n_i'], ftype))
            addLog(errmsg, errors, logger, logType='error')
        return False
    else:
        if ftype == 'metadata':
            # return std_info_fname to continue checking
            return False
        if ftype == 'das':
            models = ("incomplete or inconsistent with "
                      "Array_t_%(array)s:sensor_model=%(smodel)s "
                      "Array_t_%(array)s:das_model=%(dmodel)s "
                      "Array_t_%(array)s:sr=%(spr)s "
                      "Array_t_%(array)s:srm=%(sprm)s "
                      "Array_t_%(array)s:gain=%(gain)s "
                      "Array_t_%(array)s:cha=%(cha_code)s. "
                      "Please check with format "
                      "[das_model]_[sr]_[srm]_[gain] or "
                      "[das_model]_[sensor_model]_[sr][cha]")
        if ftype == 'sensor':
            models = ("inconsistent with "
                      "Array_t_%(array)s:sensor_model=%(smodel)s")
        errmsg = ("{0}Response_t[{1}]:response_file_{2}_a '{3}' is {4}."
                  ).format(header,
                           info['n_i'],
                           ftype,
                           std_response_fname,
                           models % info)
        addLog(errmsg, errors, logger, logType='error')
        return False


def check_response_info(info, ph5, checked_data_files, errors, logger):
    """
    Check in response info for each station entry if the response filenames are
    correct (das filename created by metadata or das/sensor filename
    created by resp_load) and the response data are loaded.
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ph5: ph5 object
    :param checked_data_files: set of resp filenames that check_response_info()
        has run for it
    :param errors: list of errors from caller
    :param logger: logger of the caller
    :return:
        False, list of error messages if no response data loaded
        (d_path, s_path) in which d_path and s_path are response paths for
            das or sensor if response data are loaded for the file name stated
            in response table
    """
    Response_t = ph5.get_response_t_by_n_i(info['n_i'])
    header = ("array {0} station {1}, channel {2}: ").format(info['array'],
                                                             info['sta'],
                                                             info['cha_id'])
    if Response_t is None:
        errmsg = ("%sResponse_t has no entry for n_i=%s"
                  % (header, info['n_i']))
        return False, [errmsg]
    if info['n_i'] == -1:
        # metadata no response signal
        errmsg = ("%sResponse_t[-1]:Metadata response with n_i=-1 has no "
                  "response data." % header)
        return False, [errmsg]

    # check resp file from metadata
    ret = check_resp_file_name(
        Response_t, info, header, 'metadata', errors, logger)
    if not ret:
        # check sensor
        check_resp_file_name(
            Response_t, info, header, 'sensor', errors, logger)

        # check das
        check_resp_file_name(
            Response_t, info, header, 'das', errors, logger)

    das_resp_path = Response_t['response_file_das_a']
    sens_resp_path = Response_t['response_file_sensor_a']
    data_errors = []

    if das_resp_path == '':
        errmsg = "%sresponse_file_das_a is blank." % header
        data_errors.append(errmsg)
    else:
        try:
            check_resp_data(ph5.ph5, das_resp_path, header,
                            checked_data_files, info['n_i'])
        except Exception as e:
            data_errors.append(str(e))
    if sens_resp_path != '':
        try:
            check_resp_data(ph5.ph5, sens_resp_path, header,
                            checked_data_files, info['n_i'])
        except Exception as e:
            data_errors.append(str(e))
    if data_errors != []:
        return False, data_errors
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
        return errmsg
    return True


def check_has_response_filename(Response_t, errors, logger):
    # check if Response table contain any response file name
    for entry in Response_t['rows']:
        if entry['response_file_das_a'] != '':
            return True
    errmsg = ("Response table does not contain any response file names. "
              "Check if resp_load has been run or if metadatatoph5 input "
              "contained response information.")
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
