#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to match trajectories on consecutive days.
"""

import sys
import os
import errno
import numpy as np
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, NEW_ID_FIELDS
from pru.trajectory_files import create_matching_ids_filename, PREV_DAY
from pru.logger import logger

log = logger(__name__)

DEFAULT_MAXIMUM_TIME_DELTA = 150  # 2.5 minutes
""" The default maximum time difference, in seconds. """

input_filenames = ['prev flights file',
                   'flights file']
""" The filenames required by the application. """


def add_matches(flight_matches, flight_ids):
    """
    Add new matches to the flight_ids dict.

    Returns the number of newly matched flights.

    """
    matches = 0

    for i in flight_matches.index:
        prev_id = flight_matches.loc[i, 'FLIGHT_ID_x']
        next_id = flight_matches.loc[i, 'FLIGHT_ID_y']
        if next_id not in flight_ids:
            flight_ids[next_id] = prev_id
            matches += 1

    return matches


def match_overnight_flights(filenames,
                            max_time_difference=DEFAULT_MAXIMUM_TIME_DELTA):
    """
    Match overnight flights with the same aircrfat address or callsign.

    The end of the previous flight must be within max_time_difference of the
    start of the next positions flight.

    """
    prev_flights_filename = filenames[0]
    next_flights_filename = filenames[1]

    # Extract date strings from the input filenames and validate them
    input_date_strings = [''] * len(input_filenames)
    for i in range(len(input_filenames)):
        filename = filenames[i]
        input_date_strings[i] = read_iso8601_date_string(filename)
        if is_valid_iso8601_date(input_date_strings[i]):
            log.info('%s: %s', input_filenames[i], filename)
        else:
            log.error('%s: %s, invalid date: %s',
                      input_filenames[i], filename, input_date_strings[i])
            return errno.EINVAL

    # Ensure that all files are for the correct dates
    if (input_date_strings[0] >= input_date_strings[1]):
        log.error("Files are not for the correct dates prev flights date: %s, "
                  "flights date: %s",
                  input_date_strings[0], input_date_strings[1])
        return errno.EINVAL

    next_days_date = input_date_strings[1]

    log.info('Maximum time difference: %f', max_time_difference)

    ############################################################################
    # Read the flight files

    # Read previous flights into a pandas DataFrame
    prev_flights_df = pd.DataFrame()
    try:
        prev_flights_df = pd.read_csv(prev_flights_filename,
                                      parse_dates=['PERIOD_START', 'PERIOD_FINISH'],
                                      converters={'FLIGHT_ID': lambda x: UUID(x)},
                                      usecols=['FLIGHT_ID', 'CALLSIGN',
                                               'AIRCRAFT_ADDRESS', 'ADEP', 'ADES',
                                               'PERIOD_START', 'PERIOD_FINISH'])
    except EnvironmentError:
        log.error('could not read file: %s', prev_flights_filename)
        return errno.ENOENT

    log.info('cpr flights read ok')

    # Read next flights into a pandas DataFrame
    next_flights_df = pd.DataFrame()
    try:
        next_flights_df = pd.read_csv(next_flights_filename,
                                      parse_dates=['PERIOD_START', 'PERIOD_FINISH'],
                                      converters={'FLIGHT_ID': lambda x: UUID(x)},
                                      usecols=['FLIGHT_ID', 'CALLSIGN',
                                               'AIRCRAFT_ADDRESS', 'ADEP', 'ADES',
                                               'PERIOD_START', 'PERIOD_FINISH'])
    except EnvironmentError:
        log.error('could not read file: %s', next_flights_filename)
        return errno.ENOENT

    log.info('adsb flights read ok')

    # Dict to hold the flight ids
    flight_ids = {}

    # Get the prev flights with aircraft addresses
    prev_flights_aa = prev_flights_df.loc[prev_flights_df['AIRCRAFT_ADDRESS'].notnull()]
    next_flights_aa = next_flights_df.loc[next_flights_df['AIRCRAFT_ADDRESS'].notnull()]

    ############################################################################
    # Match the flights

    # match previous and next flights on aircraft address and times wihin max_time_difference
    merge_aa = pd.merge(prev_flights_aa, next_flights_aa, on='AIRCRAFT_ADDRESS')
    merge_aa_time = merge_aa.loc[((merge_aa.PERIOD_START_y - merge_aa.PERIOD_FINISH_x) /
                                  np.timedelta64(1, 's')) < max_time_difference]

    # add aircraft address matches
    aa_matches = add_matches(merge_aa_time, flight_ids)
    log.info('aircraft address matches: %d, flight_ids: %d',
             aa_matches, len(flight_ids))

    # match previous and next flights on callsign and times wihin max_time_difference
    merge_cs = pd.merge(prev_flights_df, next_flights_df, on='CALLSIGN')
    merge_cs_time = merge_cs.loc[((merge_cs.PERIOD_START_y - merge_cs.PERIOD_FINISH_x) /
                                  np.timedelta64(1, 's')) < max_time_difference]

    # add callsign matches
    cs_matches = add_matches(merge_cs_time, flight_ids)
    log.info('callsign matches: %d, total matches:%d, flight_ids: %d',
             cs_matches, aa_matches + cs_matches, len(flight_ids))

    ############################################################################
    # Output the previous day ids
    prev_ids_filename = create_matching_ids_filename(PREV_DAY, next_days_date)
    try:
        with open(prev_ids_filename, 'w') as file:
            file.write(NEW_ID_FIELDS)
            for key, value in flight_ids.items():
                print(key, value, sep=',', file=file)

        log.info('written file: %s', prev_ids_filename)
    except EnvironmentError:
        log.error('could not write file: %s', prev_ids_filename)
        return errno.EACCES

    log.info('overnight flight matching complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>'
              ' [maximum time difference]')
        sys.exit(errno.EINVAL)

    max_time_difference = DEFAULT_MAXIMUM_TIME_DELTA
    if len(sys.argv) > (len(input_filenames) + 1):
        max_time_difference = float(sys.argv[3])

    error_code = match_overnight_flights(sys.argv[1:3],
                                         max_time_difference)
    if error_code:
        sys.exit(error_code)
