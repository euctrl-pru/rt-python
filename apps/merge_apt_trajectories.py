#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to merge Eurocontrol APDS data and a days merged trajectories.
"""

import sys
import os
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, split_dual_date, ISO8601_DATETIME_FORMAT
from pru.trajectory_files import create_merge_apds_output_filenames
from pru.trajectory_merging import \
    read_dataframe_with_new_ids, replace_old_flight_ids
from pru.logger import logger

log = logger(__name__)


def get_apds_items_with_new_ids(apds_filename, ids_df):
    """
    Reads items (positions and events) from apds_filename into a pandas Dataframe
    and merge with ids_df on FLIGHT_ID.
    Drops the old FLIGHT_ID column and replaces it with the NEW_FLIGHT_ID
    column renamed to FLIGHT_ID.

    Returns a pandas DataFrame containing items with the new flight ids in
    the FLIGHT_ID column.
    """
    apds_df = read_dataframe_with_new_ids(apds_filename, ids_df)
    replace_old_flight_ids(apds_df)
    return apds_df


def merge_items(day_filename, apds_filename, ids_df, log):
    """
    Merges day and apds files containing items (positions or events).

    Returns: a pandas DataFrame containing the new items.
    Note: the items are sorted in flight id and time order.
    """
    apds_items_df = get_apds_items_with_new_ids(apds_filename, ids_df)
    if not len(apds_items_df):
        log.error('could not match apds items from: %s', apds_filename)
        return pd.DataFrame()

    day_items_df = pd.DataFrame()
    try:
        day_items_df = pd.read_csv(day_filename,
                                   converters={'FLIGHT_ID': lambda x: UUID(x)},
                                   parse_dates=['TIME'],
                                   memory_map=True)
    except EnvironmentError:
        log.error('could not read daily file: %s', day_filename)
        return pd.DataFrame()

    items_df = pd.concat([day_items_df, apds_items_df], ignore_index=True)
    items_df.sort_values(by=['FLIGHT_ID', 'TIME'], inplace=True)

    return items_df


input_filenames = ['apds ids file',
                   'daily positions file',
                   'apds positions file',
                   'daily events file',
                   'apds events file']
""" The filenames required by the application. """


def merge_apds_trajectories(filenames):

    apds_ids_filename = filenames[0]

    day_points_filename = filenames[1]
    apds_points_filename = filenames[2]

    day_events_filename = filenames[3]
    apds_events_filename = filenames[4]

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

    days_date = input_date_strings[0]
    points_finish_date = input_date_strings[2]

    # Extract the start date string from the filename and validate it
    points_start_date, _ = split_dual_date(os.path.basename(apds_points_filename))
    if not is_valid_iso8601_date(points_start_date):
        log.error('apds points file: %s, invalid start date: %s',
                  apds_points_filename, points_start_date)
        return errno.EINVAL

    # Extract the start date string from the filename and validate it
    events_start_date, _ = split_dual_date(os.path.basename(apds_events_filename))
    if not is_valid_iso8601_date(events_start_date):
        log.error('apds events file: %s, invalid start date: %s',
                  apds_events_filename, events_start_date)
        return errno.EINVAL

    # Ensure that all files are for the same date
    if (days_date != input_date_strings[1]) or \
            (days_date != input_date_strings[3]):
        log.error('Files are not for the same dates!'
                  ' Ids date: %s, Day Positions date: %s, Day Events date: %s',
                  days_date, input_date_strings[1], input_date_strings[3])
        return errno.EINVAL

    # Ensure day is within APDS date range
    if not (points_start_date <= days_date <= points_finish_date):
        log.error("Daily files are not in APDS data range!"
                  " Daily date: %s, APDS range: %s to %s",
                  days_date, points_start_date, points_finish_date)
        return errno.EINVAL

    ############################################################################
    # Merge positions and events

    # Read apds ids into a pandas DataFrame
    apds_ids_df = pd.DataFrame()
    try:
        apds_ids_df = pd.read_csv(apds_ids_filename, index_col='FLIGHT_ID',
                                  converters={'NEW_FLIGHT_ID': lambda x: UUID(x)},
                                  memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', apds_ids_filename)
        return errno.ENOENT

    points_df = merge_items(day_points_filename, apds_points_filename,
                            apds_ids_df, log)
    if not len(points_df):
        log.error('Error merging points')
        return errno.ENOENT

    events_df = merge_items(day_events_filename, apds_events_filename,
                            apds_ids_df, log)
    if not len(events_df):
        log.error('Error merging events')
        return errno.ENOENT

    ############################################################################
    # Output Data

    # Output the merged positions
    output_files = create_merge_apds_output_filenames(days_date)
    points_file = output_files[0]
    try:
        points_df.to_csv(points_file, index=False,
                         date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', points_file)
    except EnvironmentError:
        log.error('could not write file: %s', points_file)
        return errno.EACCES

    # Output the merged events
    events_file = output_files[1]
    try:
        events_df.to_csv(events_file, index=False,
                         date_format=ISO8601_DATETIME_FORMAT)
        log.info('written file: %s', events_file)
    except EnvironmentError:
        log.error('could not write file: %s', events_file)
        return errno.EACCES

    log.info('apds merging complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = merge_apds_trajectories(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
