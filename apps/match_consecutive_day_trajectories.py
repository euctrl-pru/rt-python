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
from pru.ecef_functions import calculate_EcefPoints
from pru.trajectory_functions import compare_trajectory_positions
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, NEW_ID_FIELDS
from pru.trajectory_files import create_matching_ids_filename, PREV_DAY
from pru.logger import logger

log = logger(__name__)

DEFAULT_MAXIMUM_TIME_DELTA = 150  # 2.5 minutes
""" The default maximum time difference, in seconds. """


def verify_matches(flight_matches, positions1, positions2, flight_ids, delta_time):
    """
    Verifies the pairs of flight ids in flight_matches by calling
    compare_trajectory_positions with the cpr_positions and adsb_positions
    of each flight against the delta_time threshold.

    It adds new matches to the flight_ids dicts and returns the number of newly
    matched flights.
    """
    matches = 0
    next_pos_match = pd.merge(positions2, flight_matches,
                              left_index=True, right_on='FLIGHT_ID_y')

    for next_id, next_pos in next_pos_match.groupby('FLIGHT_ID_y'):
        # Ensure that next_pos is new has more than one value!
        if next_id not in flight_ids and \
                isinstance(next_pos['TIME_SOURCE'], pd.Series):

            next_times = next_pos['TIME_SOURCE'].values
            next_points = calculate_EcefPoints(next_pos['LAT'].values,
                                               next_pos['LON'].values)
            next_alts = next_pos['ALT'].values

            for prev_id in next_pos['FLIGHT_ID_x'].unique():
                prev_pos = positions1.loc[prev_id]
                # Ensure that prev_pos has more than one value!
                if isinstance(prev_pos['TIME_SOURCE'], pd.Series):
                    prev_times = prev_pos['TIME_SOURCE'].values
                    prev_points = calculate_EcefPoints(prev_pos['LAT'].values,
                                                       prev_pos['LON'].values)
                    prev_alts = prev_pos['ALT'].values
                    valid_match = compare_trajectory_positions(next_times, prev_times,
                                                               next_points, prev_points,
                                                               next_alts, prev_alts,
                                                               time_threshold=delta_time)
                    if (valid_match):
                        matches += 1
                        flight_ids[next_id] = prev_id

    return matches


input_filenames = ['prev flights file',
                   'next flights file',
                   'prev positions file',
                   'next positions file']
""" The filenames required by the application. """


def match_consecutive_day_trajectories(filenames,
                                       max_time_difference=DEFAULT_MAXIMUM_TIME_DELTA):

    prev_flights_filename = filenames[0]
    next_flights_filename = filenames[1]

    # Note positions files must be 'clean'
    prev_positions_filename = filenames[2]
    next_positions_filename = filenames[3]

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
    if (input_date_strings[0] != input_date_strings[2]) \
            or (input_date_strings[1] != input_date_strings[3]) \
            or (input_date_strings[0] >= input_date_strings[1]):
        log.error("Files are not for the correct dates prev flights date: %s, "
                  "next flights date: %s  prev Positions date: %s, "
                  "next Positions date: %s",
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3])
        return errno.EINVAL

    next_days_date = input_date_strings[1]

    log.info('Maximum time difference: %f', max_time_difference)

    ############################################################################
    # Read the files

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

    # Read previous points into a pandas DataFrame
    prev_points_df = pd.DataFrame()
    try:
        prev_points_df = pd.read_csv(prev_positions_filename,
                                     parse_dates=['TIME_SOURCE'], index_col='FLIGHT_ID',
                                     converters={'FLIGHT_ID': lambda x: UUID(x)},
                                     usecols=['FLIGHT_ID', 'TIME_SOURCE',
                                              'LAT', 'LON', 'ALT'])
    except EnvironmentError:
        log.error('could not read file: %s', prev_positions_filename)
        return errno.ENOENT

    log.info('prev points read ok')

    # Read the next points into a pandas DataFrame
    next_points_df = pd.DataFrame()
    try:
        next_points_df = pd.read_csv(next_positions_filename,
                                     parse_dates=['TIME_SOURCE'], index_col='FLIGHT_ID',
                                     converters={'FLIGHT_ID': lambda x: UUID(x)},
                                     usecols=['FLIGHT_ID', 'TIME_SOURCE',
                                              'LAT', 'LON', 'ALT'])
    except EnvironmentError:
        log.error('could not read file: %s', next_positions_filename)
        return errno.ENOENT

    log.info('next points read ok')

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

    # verify aircraft address matches
    aa_matches = verify_matches(merge_aa_time, prev_points_df, next_points_df,
                                flight_ids, max_time_difference)
    log.info('aircraft address matches: %d, flight_ids: %d',
             aa_matches, len(flight_ids))

    # match previous and next flights on callsign and times wihin max_time_difference
    merge_cs = pd.merge(prev_flights_df, next_flights_df, on='CALLSIGN')
    merge_cs_time = merge_cs.loc[((merge_cs.PERIOD_START_y - merge_cs.PERIOD_FINISH_x) /
                                  np.timedelta64(1, 's')) < max_time_difference]

    # verify callsign matches
    cs_matches = verify_matches(merge_cs_time, prev_points_df, next_points_df,
                                flight_ids, max_time_difference)
    log.info('callsign matches: %d, total matches:%d, flight_ids: %d',
             cs_matches, aa_matches + cs_matches, len(flight_ids))

    # match previous and next flights on departure, destination and overlaping start & end times
    merge_dep_des = pd.merge(prev_flights_df, next_flights_df, on=['ADEP', 'ADES'])
    merge_dep_des_time = merge_cs.loc[((merge_dep_des.PERIOD_START_y - merge_dep_des.PERIOD_FINISH_x) /
                                       np.timedelta64(1, 's')) < max_time_difference]

    # verify departure and destination airport matches
    apt_matches = verify_matches(merge_dep_des_time, prev_points_df, next_points_df,
                                 flight_ids, max_time_difference)
    log.info('airport matches: %d, total matches:%d, flight_ids: %d',
             apt_matches, apt_matches + aa_matches + cs_matches, len(flight_ids))

    # Output the previous day ids
    prev_ids_filename = create_matching_ids_filename(PREV_DAY, next_days_date)
    try:
        with open(prev_ids_filename, 'w') as file:
            file.write(NEW_ID_FIELDS)
            for key, value in flight_ids.items():
                print(key, value, sep=',', file=file)
    except EnvironmentError:
        log.error('could not write file: %s', prev_ids_filename)
        return errno.EACCES

    log.info('written file: %s', prev_ids_filename)

    log.info('consecutive day matching complete')

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
        max_time_difference = float(sys.argv[5])

    error_code = match_consecutive_day_trajectories(sys.argv[1:5],
                                                    max_time_difference)
    if error_code:
        sys.exit(error_code)
