#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Merges CPR and ADS-B flights and positions data.
"""

import sys
import os
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import \
    is_valid_iso8601_date, ISO8601_DATETIME_FORMAT, \
    read_iso8601_date_string, create_iso8601_csv_filename
from pru.trajectory_files import create_merge_cpr_adsb_output_filenames
from pru.trajectory_merging import \
    read_dataframe_with_new_ids, replace_old_flight_ids
from pru.logger import logger

log = logger(__name__)


def get_flights_with_new_ids(flights_filename, ids_df):
    """
    Reads flights from flights_filename into a pandas Dataframe and merge
    with ids_df on FLIGHT_ID.
    Drops the old FLIGHT_ID column and replaces it with the NEW_FLIGHT_ID
    column renamed to FLIGHT_ID.

    Returns a pandas DataFrame containing flights with the new flight ids in
    the FLIGHT_ID column.
    """
    flights_df = read_dataframe_with_new_ids(flights_filename, ids_df,
                                             date_fields=['PERIOD_START',
                                                          'PERIOD_FINISH'])
    replace_old_flight_ids(flights_df)
    return flights_df


def merge_flights(flights1_df, flights2_df):
    """
    Concatenates the flights data frames, drops duplicate flight ids and
    sorts by flight id.
    """
    flights_df = pd.concat([flights1_df, flights2_df], ignore_index=True)
    flights_df.drop_duplicates(subset='FLIGHT_ID', inplace=True)
    flights_df.set_index('FLIGHT_ID', drop=False, inplace=True)
    flights_df.sort_index(inplace=True)
    return flights_df


def get_merged_flights(flights1_filename, flights2_filename, ids1_df, ids2_df):
    """
    Reads the flights from flights1_filename and flights2_filename, replaces
    their flight ids with ids from ids1_df and ids2_df and concatenates them
    into a single DataFrame.

    Note: flights1 are concatenated on the end of flights 2, so that when
    duplicate are droped, flights 2 flights are given preference
    """
    return merge_flights(get_flights_with_new_ids(flights2_filename, ids2_df),
                         get_flights_with_new_ids(flights1_filename, ids1_df))


def merge_positions(positions1_df, positions2_df):
    """
    Merges pandas DataFrames containing positions: positions_1 and positions_2

    Returns: a pandas DataFrame containing the new positions.
    Note: the postions are sorted in new flight id and time order.
    """
    new_positions_df = pd.concat([positions1_df, positions2_df], ignore_index=True)
    new_positions_df.sort_values(by=['NEW_FLIGHT_ID', 'TIME'], inplace=True)
    return new_positions_df


def get_merged_positions(positions1_filename, positions2_filename, ids1_df, ids2_df):
    """
    Reads the positions files, changes their flight ids, merges and sorts them.
    """
    return merge_positions(read_dataframe_with_new_ids(positions1_filename, ids1_df),
                           read_dataframe_with_new_ids(positions2_filename, ids2_df))


def update_flight_data(flights_df, positions_df):
    """
    Update the flights_df with the FLIGHT_IDs SSR_CODEs and starts and ends
    of the positions periods.
    """
    for flight_id, positions in positions_df.groupby('NEW_FLIGHT_ID'):

        if flight_id in flights_df.index:
            flight_ids = positions['FLIGHT_ID'].drop_duplicates()
            flights_df.at[flight_id, 'SOURCE_IDS'] = flight_ids.values

            ssr_codes = positions['SSR_CODE'].drop_duplicates()
            flights_df.at[flight_id, 'SSR_CODES'] = ssr_codes.values

            times = positions['TIME']
            start_time = times.iloc[0]
            flights_df.at[flight_id, 'PERIOD_START'] = start_time
            finish_time = times.iloc[-1]
            flights_df.at[flight_id, 'PERIOD_FINISH'] = finish_time


input_filenames = ['cpr ids file',
                   'adsb ids file',
                   'cpr flights file',
                   'adsb flights file',
                   'cpr positions file',
                   'adsb positions file',
                   'cpr events file']
""" The filenames required by the application. """


def merge_cpr_adsb_trajectories(filenames):

    cpr_ids_filename = filenames[0]
    adsb_ids_filename = filenames[1]

    cpr_flights_filename = filenames[2]
    adsb_flights_filename = filenames[3]

    # Note positions files must be clean
    cpr_positions_filename = filenames[4]
    adsb_positions_filename = filenames[5]

    cpr_events_filename = filenames[6]

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

    # Ensure that all files are for the same date
    if input_date_strings[1:] != input_date_strings[:-1]:
        log.error("Files are not for the same dates: %s,%s,%s,%s,%s,%s,%s",
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3],
                  input_date_strings[4], input_date_strings[5],
                  input_date_strings[6])
        return errno.EINVAL

    ############################################################################
    # Read the files

    # Read the Id files
    cpr_ids_df = pd.DataFrame()
    try:
        cpr_ids_df = pd.read_csv(cpr_ids_filename, index_col='FLIGHT_ID',
                                 converters={'NEW_FLIGHT_ID': lambda x: UUID(x)},
                                 memory_map=True)
        cpr_ids_df.sort_index(inplace=True)
    except EnvironmentError:
        log.error('could not read file: %s', cpr_ids_filename)
        return errno.ENOENT

    adsb_ids_df = pd.DataFrame()
    try:
        adsb_ids_df = pd.read_csv(adsb_ids_filename, index_col='FLIGHT_ID',
                                  converters={'NEW_FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
        cpr_ids_df.sort_index(inplace=True)
    except EnvironmentError:
        log.error('could not read file: %s', adsb_ids_filename)
        return errno.ENOENT

    log.info('read ids files: %s,%s', cpr_ids_filename, adsb_ids_filename)

    # Read and merge the flights
    flights_df = pd.DataFrame()
    try:
        flights_df = get_merged_flights(cpr_flights_filename,
                                        adsb_flights_filename,
                                        cpr_ids_df, adsb_ids_df)
    except EnvironmentError:
        log.error('could not read file: %s or %s',
                  cpr_flights_filename, adsb_flights_filename)
        return errno.ENOENT

    log.info('read and merged flights files: %s,%s',
             cpr_flights_filename, adsb_flights_filename)

    # Read and merge the position
    positions_df = pd.DataFrame()
    try:
        positions_df = get_merged_positions(cpr_positions_filename,
                                            adsb_positions_filename,
                                            cpr_ids_df, adsb_ids_df)
    except EnvironmentError:
        log.error('could not read file: %s or %s',
                  cpr_positions_filename, adsb_positions_filename)
        return errno.ENOENT

    # Read and merge the positions
    log.info('read and merged positions files: %s,%s',
             cpr_positions_filename, adsb_positions_filename)

    # Read and merge the events
    events_df = pd.DataFrame()
    try:
        events_df = read_dataframe_with_new_ids(cpr_events_filename, cpr_ids_df)
        replace_old_flight_ids(events_df)
    except EnvironmentError:
        log.error('could not read file:  %s', cpr_events_filename)
        return errno.ENOENT

    # Read and merge the positions
    log.info('read and merged events file: %s', cpr_events_filename)

    update_flight_data(flights_df, positions_df)

    # Output the flights
    output_files = create_merge_cpr_adsb_output_filenames(input_date_strings[0])
    output_flights_filename = output_files[0]
    try:
        flights_df.to_csv(output_flights_filename, index=False,
                          date_format=ISO8601_DATETIME_FORMAT)
    except EnvironmentError:
        log.error('could not write file: %s', output_flights_filename)
        return errno.EACCES

    log.info('written file: %s', output_flights_filename)

    # Convert the positions prior to output
    replace_old_flight_ids(positions_df)
    output_positions_filename = output_files[1]
    try:
        positions_df.to_csv(output_positions_filename, index=False,
                            date_format=ISO8601_DATETIME_FORMAT)
    except EnvironmentError:
        log.error('could not write file: %s', output_positions_filename)
        return errno.EACCES

    log.info('written file: %s', output_positions_filename)

    # Output the events
    output_events_filename = output_files[2]
    try:
        events_df.to_csv(output_events_filename, index=False,
                         date_format=ISO8601_DATETIME_FORMAT)
    except EnvironmentError:
        log.error('could not write file: %s', output_events_filename)
        return errno.EACCES

    log.info('written file: %s', output_events_filename)

    log.info('merging complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = merge_cpr_adsb_trajectories(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
