#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Extract flights, positions and events data that belongs to the previous day.
"""

import sys
import os
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import \
    is_valid_iso8601_date, iso8601_previous_day, ISO8601_DATETIME_FORMAT, \
    has_bz2_extension, BZ2_FILE_EXTENSION, read_iso8601_date_string
from pru.trajectory_files import CPR_FR24, create_positions_filename, \
    create_events_filename
from pru.trajectory_merging import replace_old_flight_ids
from pru.logger import logger

log = logger(__name__)

BZ2_LENGTH = len(BZ2_FILE_EXTENSION)


def extract_next_day_items(filename, ids_df, date_fields=[]):
    """
    Read filename into a pandas Dataframe and extract items in ids_df.

    It reads items (flights, positions or events) from filename into a
    pandas Dataframe and merges the items with ids_df on FLIGHT_ID as a UUID.

    It writes a copy of the Dataframe items WITHOUT mathing ids into a file
    called 'new_' + filename

    Returns a pandas DataFrame containing items with matching ids in
    the FLIGHT_ID column, with the flight ids from the NEW_FLIGHT_ID.

    """
    # An empty data frame to return
    new_items_df = pd.DataFrame()

    next_df = pd.DataFrame()
    try:
        if date_fields:
            next_df = pd.read_csv(filename, parse_dates=date_fields,
                                  converters={'FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
        else:
            next_df = pd.read_csv(filename,
                                  converters={'FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
        log.info('%s read ok', filename)
    except EnvironmentError:
        log.error('could not read file: %s', filename)
        return new_items_df  # return empty DataFrame

    # Create a new dataframe WITHOUT any items that are in ids_df
    new_next_df = next_df[(~next_df['FLIGHT_ID'].isin(ids_df.index))]

    # Output the new next items
    new_next_filename = 'new_' + filename
    try:
        is_bz2 = has_bz2_extension(filename)
        if is_bz2:
            new_next_filename = new_next_filename[:-BZ2_LENGTH]

        new_next_df.to_csv(new_next_filename, index=False,
                           date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', new_next_filename)
    except EnvironmentError:
        log.error('could not write file: %s', new_next_filename)
        return new_items_df  # return empty DataFrame

    # get the new items from the next DataFrame
    new_items_df = pd.merge(ids_df, next_df, left_index=True, right_on='FLIGHT_ID')
    replace_old_flight_ids(new_items_df)

    return new_items_df  # return new items


################################################################################
input_filenames = ['ids file',
                   'flights file',
                   'positions file',
                   'events file', ]
""" The filenames required by the application. """


def extract_overnight_data(filenames):
    """
    Extract flights, postions and events for the previosu day from the data.

    It writes items (flights, positions or events) WITHOUT ids in the ids file
    into files with 'new_' prepended to the filename.

    It writes positions and events with ids in the ids file into positions and
    files for the previus day, with the ids replaced by the previous ids in the
    ids file.

    """
    day_ids_filename = filenames[0]

    flights_filename = filenames[1]
    positions_filename = filenames[2]
    events_filename = filenames[3]

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
            or (date != input_date_strings[3]):
        log.error("Files are not for the same dates: %s,%s,%s,%s",
                  input_date_strings[0], input_date_strings[1],
                  input_date_strings[2], input_date_strings[3])

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

    # Don't require the flights
    # Just write flights WITHOUT mathing ids into a "new" file
    _ = extract_next_day_items(flights_filename, ids_df)

    prev_positions = extract_next_day_items(positions_filename, ids_df, ['TIME'])

    # Output the new next items
    prev_date = iso8601_previous_day(date)
    overnight_positions_filename = 'overnight_' + \
        create_positions_filename(CPR_FR24, prev_date)
    try:
        prev_positions.to_csv(overnight_positions_filename, index=False,
                              date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', overnight_positions_filename)
    except EnvironmentError:
        log.error('could not write file: %s', overnight_positions_filename)
        return errno.ENOENT

    prev_events = extract_next_day_items(events_filename, ids_df, ['TIME'])
    overnight_events_filename = 'overnight_' + \
        create_events_filename(CPR_FR24, prev_date)
    try:
        prev_events.to_csv(overnight_events_filename, index=False,
                           date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', overnight_events_filename)
    except EnvironmentError:
        log.error('could not write file: %s', overnight_events_filename)
        return errno.ENOENT

    log.info('extraction complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = extract_overnight_data(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
