#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Merges merged flights, positions and events data on consecutive days.
"""

import sys
import os
import gc
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import \
    is_valid_iso8601_date, ISO8601_DATETIME_FORMAT, \
    has_bz2_extension, BZ2_FILE_EXTENSION, read_iso8601_date_string
from pru.trajectory_merging import replace_old_flight_ids
from pru.logger import logger

log = logger(__name__)

BZ2_LENGTH = len(BZ2_FILE_EXTENSION)


def get_next_day_items(next_filename, ids_df, log, *, date_fields=[],
                       write_new_next_dataframe=True):
    """
    Reads items (flights, positions or events) from next_filename into a
    pandas Dataframe and merge the items with ids_df on FLIGHT_ID as a UUID.

    If write_new_next_dataframe is set, it writes a new copy of the Dataframe
    without the matching ids.

    Returns a pandas DataFrame containing flights with the new flight ids in
    the FLIGHT_ID column.
    """
    # An empty data frame to return
    new_items_df = pd.DataFrame()

    next_df = pd.DataFrame()
    try:
        if date_fields:
            next_df = pd.read_csv(next_filename, parse_dates=date_fields,
                                  converters={'FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
        else:
            next_df = pd.read_csv(next_filename,
                                  converters={'FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
        log.info('%s read ok', next_filename)
    except EnvironmentError:
        log.error('could not read file: %s', next_filename)
        return new_items_df  # return empty DataFrame

    if write_new_next_dataframe:
        # Create a new dataframe WITHOUT any items that are in ids_df
        new_next_df = next_df[(~next_df['FLIGHT_ID'].isin(ids_df.index))]

        # Output the new next items
        new_next_filename = 'new_' + next_filename
        try:
            is_bz2 = has_bz2_extension(next_filename)
            if is_bz2:
                new_next_filename = new_next_filename[:-BZ2_LENGTH]

            new_next_df.to_csv(new_next_filename, index=False,
                               date_format=ISO8601_DATETIME_FORMAT)
            log.info('written file: %s', new_next_filename)
        except EnvironmentError:
            log.error('could not write file: %s', new_next_filename)
            return new_items_df  # return empty DataFrame

    # Free up memory used by new_next_df
    gc.collect()

    # get the new items from the next DataFrame
    new_items_df = pd.merge(ids_df, next_df, left_index=True, right_on='FLIGHT_ID')
    replace_old_flight_ids(new_items_df)

    return new_items_df  # return new items


def update_flight_data(prev_flights_df, new_items_df):
    """
    Update the matching flights in prev_flights_df with the source flight ids,
    SSR codes and finish time of the next day's flight.

    """
    for flight_id, flight in new_items_df.groupby('FLIGHT_ID'):

        if flight_id in prev_flights_df.index:
            # append the next days, source flight ids and ssr codes

            # Currently on CPR flights are merged and the code below
            # just complctaes the formatting of the flight_ids and ssr_codes
            # flight_ids = prev_flights_df.at[flight_id, 'SOURCE_IDS']
            # flight_ids += flight['SOURCE_IDS']
            # prev_flights_df.at[flight_id, 'SOURCE_IDS'] = flight_ids.values
            #
            # ssr_codes = prev_flights_df.at[flight_id, 'SSR_CODES']
            # ssr_codes += flight['SSR_CODES']
            # prev_flights_df.at[flight_id, 'SSR_CODES'] = ssr_codes.values

            # finish at the next days finish time
            finish_time = flight['PERIOD_FINISH']
            prev_flights_df.at[flight_id, 'PERIOD_FINISH'] = finish_time.iloc[0]


def merge_flights(prev_flights_filename, next_flights_filename, ids_df, log):
    """
    Gets the next days flights that are the continuation of the previous days
    flights and merges them with the previous days flights.

    It writes the new next days and previous days flights to files prepended
    with new.

    it returns True if successful, False otherwise.
    """
    new_items_df = get_next_day_items(next_flights_filename, ids_df, log)

    # free memory used by get_next_day_items
    gc.collect()

    prev_flights_df = pd.DataFrame()
    try:
        prev_flights_df = pd.read_csv(prev_flights_filename,
                                      index_col='FLIGHT_ID',
                                      converters={'FLIGHT_ID': lambda x: UUID(x)},
                                      memory_map=True)
        log.info('%s read ok', prev_flights_filename)
    except EnvironmentError:
        log.error('could not read file: %s', prev_flights_filename)
        return False

    # merge next days flight data with the previous days flight data
    update_flight_data(prev_flights_df, new_items_df)

    # Output the new previous flights
    new_prev_flights_filename = 'new_' + prev_flights_filename
    try:
        is_bz2 = has_bz2_extension(prev_flights_filename)
        if is_bz2:
            new_prev_flights_filename = new_prev_flights_filename[:-BZ2_LENGTH]

        prev_flights_df.to_csv(new_prev_flights_filename, index=True,
                               date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', new_prev_flights_filename)
    except EnvironmentError:
        log.error('could not write file: %s', new_prev_flights_filename)
        return False

    return True


def merge_next_day_items(prev_filename, next_filename, ids_df, log):
    """
    Gets the next days items (positions or events) that are the continuation
    of the previous days items them with the previous days items.

    It writes the new next days and previous days items to files prepended
    with new.

    it returns True if successful, False otherwise.
    """
    new_items_df = get_next_day_items(next_filename, ids_df,
                                      log, date_fields=['TIME'])

    # free memory used by get_next_day_items
    gc.collect()

    prev_df = pd.DataFrame()
    try:
        prev_df = pd.read_csv(prev_filename, parse_dates=['TIME'],
                              converters={'FLIGHT_ID': lambda x: UUID(x)},
                              memory_map=True)
        log.info('%s read ok', prev_filename)
    except EnvironmentError:
        log.error('could not read file: %s', prev_filename)
        return False

    # merge the new items into the previous DataFrame
    new_prev_df = pd.concat([prev_df, new_items_df], ignore_index=True)
    new_prev_df.sort_values(by=['FLIGHT_ID', 'TIME'], inplace=True)

    # Output the new previous items
    new_prev_filename = 'new_' + prev_filename
    try:
        is_bz2 = has_bz2_extension(prev_filename)
        if is_bz2:
            new_prev_filename = new_prev_filename[:-BZ2_LENGTH]

        new_prev_df.to_csv(new_prev_filename, index=False,
                           date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', new_prev_filename)
    except EnvironmentError:
        log.error('could not write file: %s', new_prev_filename)
        return False

    return True


################################################################################
input_filenames = ['daily ids file',
                   'prev flights file',
                   'next flights file',
                   'prev positions file',
                   'next positions file',
                   'prev events file',
                   'next events file', ]
""" The filenames required by the application. """


def merge_consecutive_day_trajectories(filenames):

    day_ids_filename = filenames[0]

    prev_flights_filename = filenames[1]
    next_flights_filename = filenames[2]

    prev_positions_filename = filenames[3]
    next_positions_filename = filenames[4]

    prev_events_filename = filenames[5]
    next_events_filename = filenames[6]

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

    prev_date = input_date_strings[1]
    next_date = input_date_strings[2]

    if (input_date_strings[0] != next_date) \
            or (next_date <= prev_date) \
            or (prev_date != input_date_strings[3]) \
            or (prev_date != input_date_strings[5]) \
            or (next_date != input_date_strings[4]) \
            or (next_date != input_date_strings[6]):
        log.error("Files are not for the correct dates: %s,%s,%s,%s,%s,%s,%s",
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3],
                  input_date_strings[4], input_date_strings[5],
                  input_date_strings[6])
        return errno.EINVAL

    ############################################################################

    # Read the Id file
    ids_df = pd.DataFrame()
    try:
        ids_df = pd.read_csv(day_ids_filename, index_col='FLIGHT_ID',
                             converters={'FLIGHT_ID': lambda x: UUID(x),
                                         'NEW_FLIGHT_ID': lambda x: UUID(x)},
                             memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', day_ids_filename)
        return errno.ENOENT

    # Merge flights
    if not merge_flights(prev_flights_filename, next_flights_filename, ids_df, log):
        return errno.ENOENT

    # free memory used by merge_flights
    gc.collect()

    # Merge positions
    if not merge_next_day_items(prev_positions_filename, next_positions_filename,
                                ids_df, log):
        return errno.ENOENT

    # free memory used by merge_next_day_items
    gc.collect()

    # Merge events
    if not merge_next_day_items(prev_events_filename, next_events_filename,
                                ids_df, log):
        return errno.ENOENT

    log.info('merging complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = merge_consecutive_day_trajectories(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
