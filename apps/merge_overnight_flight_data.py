#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Merges new flights, positions and events with overnight positions and events.
"""

import sys
import os
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, ISO8601_DATETIME_FORMAT
from pru.trajectory_files import RAW
from pru.logger import logger

log = logger(__name__)


def merge_overnight_items(new_filename, overnight_df):
    """
    Read the new_filename, merge with data from overnight_df and write to filename.

    Read the items (positions or events) into a DataFrame from new_filename,
    merge with the overnight_df DataFrame, sort values by FLIGHT_ID abd TIME.

    Write the merged dataframe into a file with 'new_' removed from the
    start of the filename.
    """
    # read data
    new_df = pd.DataFrame()
    try:
        new_df = pd.read_csv(new_filename, parse_dates=['TIME'],
                             converters={'FLIGHT_ID': lambda x: UUID(x)},
                             memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', new_filename)
        return new_df  # return an empty data frame

    # merge data
    merged_items_df = pd.concat([new_df, overnight_df], ignore_index=True)
    return merged_items_df.sort_values(by=['FLIGHT_ID', 'TIME'])


def update_flight_data(flights_df, positions_df):
    """ Update flights_df with the times of the last positions. """
    for flight_id, positions in positions_df.groupby('FLIGHT_ID'):

        if flight_id in flights_df.index:
            times = positions['TIME']
            finish_time = times.iloc[-1]
            flights_df.at[flight_id, 'PERIOD_FINISH'] = finish_time


################################################################################
input_filenames = ['new flights file',
                   'new positions file',
                   'overnight positions file',
                   'new events file',
                   'overnight events file', ]
""" The filenames required by the application. """


def merge_overnight_flight_data(filenames):
    """
    Merge the positions and events data and update flight data with new times.
    """
    new_flights_filename = filenames[0]

    new_positions_filename = filenames[1]
    overnight_positions_filename = filenames[2]

    new_events_filename = filenames[3]
    overnight_events_filename = filenames[4]

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

    date = input_date_strings[0]

    if (date != input_date_strings[1]) \
            or (date != input_date_strings[2]) \
            or (date != input_date_strings[3]) \
            or (date != input_date_strings[4]):
        log.error("Files are not for the correct dates: %s,%s,%s,%s,%s",
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3],
                  input_date_strings[4])
        return errno.EINVAL

    ############################################################################

    flights_df = pd.DataFrame()
    try:
        flights_df = pd.read_csv(new_flights_filename,
                                 converters={'FLIGHT_ID': lambda x: UUID(x)},
                                 memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', new_flights_filename)
        return errno.ENOENT

    overnight_pos_df = pd.DataFrame()
    try:
        overnight_pos_df = pd.read_csv(overnight_positions_filename, parse_dates=['TIME'],
                                       converters={'FLIGHT_ID': lambda x: UUID(x)},
                                       memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', overnight_positions_filename)
        return errno.ENOENT

    # Update the flight data with the new times of the overnight positions
    update_flight_data(flights_df, overnight_pos_df)

    flights_filename = new_flights_filename[4:]
    try:
        flights_df.to_csv(flights_filename, index=False,
                          date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', flights_filename)
    except EnvironmentError:
        log.error('could not write file: %s', flights_filename)
        return errno.ENOENT

    ############################################################################

    # Now merge the positions
    merged_positions = merge_overnight_items(new_positions_filename, overnight_pos_df)
    if merged_positions.empty:
        log.error('Error merging: %s', new_positions_filename)
        return errno.ENOENT

    # write merged position data
    raw_positions_filename = '_'.join([RAW, new_positions_filename[4:]])
    try:
        merged_positions.to_csv(raw_positions_filename, index=False,
                                date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', raw_positions_filename)
    except EnvironmentError:
        log.error('could not write file: %s', raw_positions_filename)
        return errno.ENOENT

    ############################################################################

    # # Merge the events
    overnight_events_df = pd.DataFrame()
    try:
        overnight_events_df = pd.read_csv(overnight_events_filename,
                                          parse_dates=['TIME'],
                                          converters={'FLIGHT_ID': lambda x: UUID(x)},
                                          memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', overnight_events_filename)
        return errno.ENOENT

    merged_events = merge_overnight_items(new_events_filename, overnight_events_df)
    if merged_events.empty:
        log.error('Error merging: %s', new_events_filename)
        return errno.ENOENT

    events_filename = new_events_filename[4:]
    try:
        merged_events.to_csv(events_filename, index=False,
                             date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', events_filename)
    except EnvironmentError:
        log.error('could not write file: %s', events_filename)
        return errno.ENOENT

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = merge_overnight_flight_data(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
