#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to match Eurocontrol Correlated Position Report (CPR) and ADS-B trajectories.
"""

import sys
import os
import errno
import pandas as pd
import uuid
from via_sphere import global_Point3d
from pru.trajectory_matching import compare_trajectory_positions
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, NEW_ID_FIELDS
from pru.trajectory_files import create_match_cpr_adsb_output_filenames
from pru.logger import logger

log = logger(__name__)

DEFAULT_MATCHING_DISTANCE_THRESHOLD = 3.0
'Maximum distance between points. Nautical Miles'

DEFAULT_MATCHING_ALTITUDE_THRESHOLD = 50000.0
"""
Maximum altitude between points. Feet
Note: currently set to 50,000 feet to disable altitude proximity testing.
"""


def verify_flight_matches(flight_matches, cpr_positions, adsb_positions,
                          cpr_ids, adsb_ids, merge_ids, distance_threshold,
                          alt_threshold):
    """
    Verifies the pairs of flight ids in flight_matches by calling
    compare_trajectory_positions with the cpr_positions and adsb_positions
    of each flight against the distance_threshold and alt_threshold.

    It adds new matches to the: cpr_ids, adsb_ids and merge_ids dicts and
    returns the number of newly matched flights.
    """
    matches = 0
    cpr_pos_match = pd.merge(cpr_positions, flight_matches,
                             left_index=True, right_on='FLIGHT_ID_x')

    for cpr_id, cpr_pos in cpr_pos_match.groupby('FLIGHT_ID_x'):
        # Ensure that cpr_pos has more than one value!
        if isinstance(cpr_pos['TIME'], pd.Series):
            cpr_times = cpr_pos['TIME'].values
            cpr_points = global_Point3d(cpr_pos['LAT'], cpr_pos['LON'])
            cpr_alts = cpr_pos['ALT'].values

            for adsb_id in cpr_pos['FLIGHT_ID_y'].unique():
                match_id = 0
                # Search for previous matches and set match_id accordingly
                if cpr_id in cpr_ids:  # previous CPR match
                    match_id = cpr_ids[cpr_id]
                    if adsb_id in adsb_ids:  # and a previous ADS-B match
                        if match_id == adsb_ids[adsb_id]:
                            continue  # match found previously
                        else:  # a new match to merge between existing matches
                            merge_ids[adsb_ids[adsb_id]] = match_id
                elif adsb_id in adsb_ids:  # previous ADS-B match only
                    match_id = adsb_ids[adsb_id]
                else:  # not matched previously
                    match_id = uuid.uuid4()

                # Ensure that adsb_id exists in adsb_positions
                adsb_pos = adsb_positions.loc[adsb_id]
                # Ensure that adsb_pos has more than one value!
                if isinstance(adsb_pos['TIME'], pd.Series):
                    adsb_times = adsb_pos['TIME'].values
                    adsb_points = global_Point3d(adsb_pos['LAT'], adsb_pos['LON'])
                    adsb_alts = adsb_pos['ALT'].values

                    # compare positions to validate the match
                    valid_match = \
                        compare_trajectory_positions(cpr_times, adsb_times,
                                                     cpr_points, adsb_points,
                                                     cpr_alts, adsb_alts,
                                                     distance_threshold=distance_threshold,
                                                     alt_threshold=alt_threshold)
                    if (valid_match):
                        matches += 1

                        if cpr_id not in cpr_ids:
                            cpr_ids[cpr_id] = match_id

                        if adsb_id not in adsb_ids:
                            adsb_ids[adsb_id] = match_id

    return matches


def merge_matches(flight_ids, merge_ids):
    """
    Replace any flight_ids values that are in the merge_ids keys with the
    merge_ids value.
    """
    for key, value in flight_ids.items():
        if value in merge_ids:
            flight_ids[key] = merge_ids[value]


def allocate_remaining_ids(flight_ids, df_fight_ids):
    """
    Allocate new UUIDS to the flights in df_fight_ids without an id in flight_ids.
    """
    for id in df_fight_ids:
        if id not in flight_ids:
            flight_ids[id] = uuid.uuid4()


input_filenames = ['cpr flights file',
                   'adsb flights file',
                   'cpr positions file',
                   'adsb positions file']
""" The filenames required by the function. """


def match_cpr_adsb_trajectories(filenames, distance_threshold=DEFAULT_MATCHING_DISTANCE_THRESHOLD,
                                alt_threshold=DEFAULT_MATCHING_ALTITUDE_THRESHOLD):

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

    # Ensure that files are all for the same date
    if input_date_strings[1:] != input_date_strings[:-1]:
        log.error('Files are not for the same date!'
                  ' CPR Flights date: %s, ADSB Flights date: %s,'
                  ' CPR Positions date: %s, ADSB Positions date: %s',
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3])
        return errno.EINVAL

    cpr_flights_filename = filenames[0]
    adsb_flights_filename = filenames[1]

    # Note positions files must be 'clean'
    cpr_positions_filename = filenames[2]
    adsb_positions_filename = filenames[3]

    log.info('Distance threshold: %f', distance_threshold)
    log.info('Altitude threshold: %f', alt_threshold)

    ############################################################################
    # Read the files

    # Read CPR flights into a pandas DataFrame
    cpr_flights_df = pd.DataFrame()
    try:
        cpr_flights_df = pd.read_csv(cpr_flights_filename,
                                     parse_dates=['PERIOD_START', 'PERIOD_FINISH'],
                                     converters={'FLIGHT_ID': lambda x: int(x)},
                                     usecols=['FLIGHT_ID', 'CALLSIGN',
                                              'AIRCRAFT_ADDRESS', 'ADEP', 'ADES',
                                              'PERIOD_START', 'PERIOD_FINISH'],
                                     memory_map=True)
        log.info('cpr flights read ok')
    except EnvironmentError:
        log.error('could not read file: %s', cpr_flights_filename)
        return errno.ENOENT

    # Read ADS-B flights into a pandas DataFrame
    adsb_flights_df = pd.DataFrame()
    try:
        adsb_flights_df = pd.read_csv(adsb_flights_filename,
                                      parse_dates=['PERIOD_START', 'PERIOD_FINISH'],
                                      converters={'FLIGHT_ID': lambda x: int(x, 16)},
                                      usecols=['FLIGHT_ID', 'CALLSIGN',
                                               'AIRCRAFT_ADDRESS', 'ADEP', 'ADES',
                                               'PERIOD_START', 'PERIOD_FINISH'],
                                      memory_map=True)
        log.info('adsb flights read ok')
    except EnvironmentError:
        log.error('could not read file: %s', adsb_flights_filename)
        return errno.ENOENT

    # Read CPR points into a pandas DataFrame
    cpr_points_df = pd.DataFrame()
    try:
        cpr_points_df = pd.read_csv(cpr_positions_filename,
                                    parse_dates=['TIME'], index_col='FLIGHT_ID',
                                    converters={'FLIGHT_ID': lambda x: int(x)},
                                    usecols=['FLIGHT_ID', 'TIME',
                                             'LAT', 'LON', 'ALT'],
                                    memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', cpr_positions_filename)
        return errno.ENOENT

    log.info('cpr points read ok')

    # Read the ADS-B points
    adsb_points_df = pd.DataFrame()
    try:
        adsb_points_df = pd.read_csv(adsb_positions_filename,
                                     parse_dates=['TIME'], index_col='FLIGHT_ID',
                                     converters={'FLIGHT_ID': lambda x: int(x, 16)},
                                     usecols=['FLIGHT_ID', 'TIME',
                                              'LAT', 'LON', 'ALT'],
                                     memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', adsb_positions_filename)
        return errno.ENOENT

    log.info('adsb points read ok')

    # Dicts to hold the flight ids
    cpr_flight_ids = {}
    adsb_flight_ids = {}
    merge_flight_ids = {}

    # Get the CPR flights with aircraft addresses
    cpr_flights_aa = cpr_flights_df.loc[cpr_flights_df['AIRCRAFT_ADDRESS'].notnull()]

    ############################################################################
    # Match the flights

    # match CPR and ADS-B flights on aircraft address and overlaping start & end times
    merge_aa = pd.merge(cpr_flights_aa, adsb_flights_df, on='AIRCRAFT_ADDRESS')
    merge_aa_time = merge_aa.loc[(merge_aa.PERIOD_START_x <= merge_aa.PERIOD_FINISH_y) &
                                 (merge_aa.PERIOD_START_y <= merge_aa.PERIOD_FINISH_x)]

    log.info('aircraft address time matches: %d', len(merge_aa_time))

    # verify aircraft address matches
    aa_matches = verify_flight_matches(merge_aa_time, cpr_points_df, adsb_points_df,
                                       cpr_flight_ids, adsb_flight_ids, merge_flight_ids,
                                       distance_threshold, alt_threshold)
    log.info('aircraft address matches: %d, cpr_ids: %d, adsb_ids: %d, merge_ids: %d',
             aa_matches, len(cpr_flight_ids), len(adsb_flight_ids), len(merge_flight_ids))

    # match CPR and ADS-B flights on callsign and overlaping start & end times
    merge_cs = pd.merge(cpr_flights_df, adsb_flights_df, on='CALLSIGN')
    merge_cs_time = merge_cs.loc[(merge_cs.PERIOD_START_x <= merge_cs.PERIOD_FINISH_y) &
                                 (merge_cs.PERIOD_START_y <= merge_cs.PERIOD_FINISH_x)]

    log.info('callsign time matches: %d', len(merge_cs_time))

    # verify callsign matches
    cs_matches = verify_flight_matches(merge_cs_time, cpr_points_df, adsb_points_df,
                                       cpr_flight_ids, adsb_flight_ids, merge_flight_ids,
                                       distance_threshold, alt_threshold)
    log.info('callsign matches: %d, cpr_ids: %d, adsb_ids: %d, merge_ids: %d',
             cs_matches, len(cpr_flight_ids), len(adsb_flight_ids), len(merge_flight_ids))

    # merge overlapping aircraft address and callsign matches
    if len(merge_flight_ids):
        merge_matches(cpr_flight_ids, merge_flight_ids)
        merge_matches(adsb_flight_ids, merge_flight_ids)
        merge_flight_ids.clear()

    # match CPR and ADS-B flights on departure, destination and overlaping start & end times
    merge_dep_des = pd.merge(cpr_flights_df, adsb_flights_df, on=['ADEP', 'ADES'])
    merge_dep_des_time = merge_cs.loc[(merge_dep_des.PERIOD_START_x <= merge_dep_des.PERIOD_FINISH_y) &
                                      (merge_dep_des.PERIOD_START_y <= merge_dep_des.PERIOD_FINISH_x)]

    # verify departure, destination matches
    dep_des_matches = verify_flight_matches(merge_dep_des_time, cpr_points_df, adsb_points_df,
                                            cpr_flight_ids, adsb_flight_ids, merge_flight_ids,
                                            distance_threshold, alt_threshold)
    log.info('airport matches: %d, cpr_ids: %d, adsb_ids: %d, merge_ids: %d',
             dep_des_matches, len(cpr_flight_ids), len(adsb_flight_ids), len(merge_flight_ids))

    # merge overlapping aircraft address, callsign and airport matches
    if len(merge_flight_ids):
        merge_matches(cpr_flight_ids, merge_flight_ids)
        merge_matches(adsb_flight_ids, merge_flight_ids)
        merge_flight_ids.clear()

    # Add unmatched flight ids to cpr_flight_ids and adsb_flight_ids
    allocate_remaining_ids(cpr_flight_ids, cpr_flights_df['FLIGHT_ID'].values)
    allocate_remaining_ids(adsb_flight_ids, adsb_flights_df['FLIGHT_ID'].values)

    ############################################################################
    # Output the matching ids

    # Output the CPR ids
    output_files = create_match_cpr_adsb_output_filenames(input_date_strings[0])
    cpr_ids_file = output_files[0]
    try:
        with open(cpr_ids_file, 'w') as file:
            file.write(NEW_ID_FIELDS)
            for key in cpr_flight_ids:
                value = cpr_flight_ids[key]
                print(key, value, sep=',', file=file)
    except EnvironmentError:
        log.error('could not write file: %s', cpr_ids_file)
        return errno.EACCES

    log.info('written file: %s', cpr_ids_file)

    # Output the ADS-B ids
    adsb_ids_file = output_files[1]
    try:
        with open(adsb_ids_file, 'w', newline='') as file:
            file.write(NEW_ID_FIELDS)
            for key in adsb_flight_ids:
                adsb_str = '0x{:06x},{}'.format(key, adsb_flight_ids[key])
                print(adsb_str, file=file)
    except EnvironmentError:
        log.error('could not write file: %s', adsb_ids_file)
        return errno.EACCES

    log.info('written file: %s', adsb_ids_file)

    log.info('matching complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>'
              ' [distance_threshold] [altitude_threshold]')
        sys.exit(errno.EINVAL)

    distance_threshold = DEFAULT_MATCHING_DISTANCE_THRESHOLD
    if len(sys.argv) > (len(input_filenames) + 1):
        distance_threshold = float(sys.argv[5])

    alt_threshold = DEFAULT_MATCHING_ALTITUDE_THRESHOLD
    if len(sys.argv) > (len(input_filenames) + 2):
        alt_threshold = float(sys.argv[6])

    error_code = match_cpr_adsb_trajectories(sys.argv[1:5],
                                             distance_threshold, alt_threshold)
    if error_code:
        sys.exit(error_code)
