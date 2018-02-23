#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to merge Eurocontrol APT data and a days merged trajectories.
"""

import sys
import os
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import \
    is_valid_iso8601_date, ISO8601_DATETIME_FORMAT, \
    read_iso8601_date_string, create_iso8601_csv_filename
from pru.trajectory_merging import \
    read_dataframe_with_new_ids, replace_old_flight_ids
from pru.logger import logger


def get_apt_items_with_new_ids(apt_filename, ids_df):
    """
    Reads items (positions and events) from apt_filename into a pandas Dataframe
    and merge with ids_df on FLIGHT_ID.
    Drops the old FLIGHT_ID column and replaces it with the NEW_FLIGHT_ID
    column renamed to FLIGHT_ID.

    Returns a pandas DataFrame containing items with the new flight ids in
    the FLIGHT_ID column.
    """
    apt_df = read_dataframe_with_new_ids(apt_filename, ids_df)
    replace_old_flight_ids(apt_df)
    return apt_df


def merge_items(day_filename, apt_filename, ids_df, log):
    """
    Merges day and apt files containing items (positions or events).

    Returns: a pandas DataFrame containing the new items.
    Note: the items are sorted in flight id and time order.
    """
    apt_items_df = get_apt_items_with_new_ids(apt_filename, ids_df)
    if not len(apt_items_df):
        log.error('could not read file: %s', apt_filename)
        return pd.DataFrame()

    day_items_df = pd.DataFrame()
    try:
        day_items_df = pd.read_csv(day_filename,
                                   converters={'FLIGHT_ID': lambda x: UUID(x)},
                                   parse_dates=['TIME_SOURCE'])
    except EnvironmentError:
        log.error('could not read file: %s', day_filename)
        return pd.DataFrame()

    items_df = pd.concat([day_items_df, apt_items_df], ignore_index=True)
    items_df.sort_values(by=['FLIGHT_ID', 'TIME_SOURCE'], inplace=True)

    return items_df


if __name__ == '__main__':

    input_filenames = ['apt ids file',
                       'daily positions file',
                       'apt positions file',
                       'daily events file',
                       'apt events file']
    """ The filenames required by the application. """

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(2)

    log = logger(app_name)

    apt_ids_filename = sys.argv[1]

    day_points_filename = sys.argv[2]
    apt_points_filename = sys.argv[3]

    day_events_filename = sys.argv[4]
    apt_events_filename = sys.argv[5]

    # Extract date strings from the input filenames and validate them
    input_date_strings = [''] * len(input_filenames)
    for i in range(len(input_filenames)):
        filename = sys.argv[i + 1]
        input_date_strings[i] = read_iso8601_date_string(filename)
        if is_valid_iso8601_date(input_date_strings[i]):
            log.info('%s: %s', input_filenames[i], filename)
        else:
            log.error('%s: %s, invalid date: %s',
                      input_filenames[i], filename, input_date_strings[i])
            sys.exit(2)

    days_date = input_date_strings[0]
    points_finish_date = input_date_strings[2]

    # Extract the start date string from the filename and validate it
    points_start_date = os.path.basename(apt_points_filename)[14:24]
    if not is_valid_iso8601_date(points_start_date):
        log.error('apt points file: %s, invalid start date: %s',
                  apt_points_filename, points_start_date)
        sys.exit(2)

    # Extract the start date string from the filename and validate it
    events_start_date = os.path.basename(apt_events_filename)[11:21]
    if not is_valid_iso8601_date(events_start_date):
        log.error('apt events file: %s, invalid start date: %s',
                  apt_events_filename, events_start_date)
        sys.exit(2)

    # Ensure that all files are for the same date
    if (days_date != input_date_strings[1]) or \
            (days_date != input_date_strings[3]):
        log.error('Files are not for the same dates!'
                  ' Ids date: %s, Day Positions date: %s, Day Events date: %s',
                  days_date, input_date_strings[1], input_date_strings[3])
        sys.exit(2)

    # Ensure day is within APT data range
    if not (points_start_date <= days_date <= points_finish_date):
        log.error("Daily files are not in APT data range!"
                  " Daily date: %s, APT range: %s to %s",
                  days_date, points_start_date, points_finish_date)
        sys.exit(2)

    ############################################################################
    # Merge positions and events

    # Read apt ids into a pandas DataFrame
    apt_ids_df = pd.DataFrame()
    try:
        apt_ids_df = pd.read_csv(apt_ids_filename, index_col='FLIGHT_ID',
                                 converters={'NEW_FLIGHT_ID': lambda x: UUID(x)})
    except EnvironmentError:
        log.error('could not read file: %s', apt_ids_filename)
        sys.exit(2)

    points_df = merge_items(day_points_filename, apt_points_filename,
                            apt_ids_df, log)
    if not len(points_df):
        log.error('Error merging points')
        sys.exit(2)

    events_df = merge_items(day_events_filename, apt_events_filename,
                            apt_ids_df, log)
    if not len(events_df):
        log.error('Error merging events')
        sys.exit(2)

    ############################################################################
    # Output Data

    # Output the merged positions
    points_file = create_iso8601_csv_filename('apt_cpr_fr24_positions_', days_date)
    try:
        points_df.to_csv(points_file, index=False,
                         date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', points_file)
    except EnvironmentError:
        log.error('could not write file: %s', points_file)
        sys.exit(2)

    # Output the merged events
    events_file = create_iso8601_csv_filename('apt_cpr_fr24_events_', days_date)
    try:
        events_df.to_csv(events_file, index=False,
                         date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', events_file)
    except EnvironmentError:
        log.error('could not write file: %s', events_file)
        sys.exit(2)

    log.info('apt merging complete')
