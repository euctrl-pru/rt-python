#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to match Eurocontrol APDS data and a days merged trajectories.
"""

import sys
import os
import errno
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, create_iso8601_csv_filename, split_dual_date
from pru.trajectory_files import APDS, create_matching_ids_filename
from pru.logger import logger

log = logger(__name__)


def match_events(day_flights_df, apds_flights_df, day_events_df, apds_events_df):
    """
    Finds common events both data sets.

    It matches on: callsign, departure airport, destination airport, event type,
    and time.

    Returns a pandas DataFrame containing the APT id and the matching days ids
    in 'FLIGHT_ID' and 'NEW_FLIGHT_ID' columns respectively.
    """
    day_flight_events_df = pd.merge(day_flights_df, day_events_df, on='FLIGHT_ID')
    apds_flight_events_df = pd.merge(apds_flights_df, apds_events_df, on='FLIGHT_ID')

    # Find events at the same time in both sets.
    apds_day_flights = pd.merge(apds_flight_events_df, day_flight_events_df,
                                on=['CALLSIGN', 'ADEP', 'ADES',
                                    'EVENT_TYPE', 'TIME_SOURCE'])

    # sort by the apds flight id and drop duplicates (if any)
    apds_day_flights.sort_values(by=['FLIGHT_ID_x'], inplace=True)
    apds_day_flights.drop_duplicates(inplace=True)

    apds_day_flights.rename(index=str, columns={'FLIGHT_ID_x': 'FLIGHT_ID',
                                                'FLIGHT_ID_y': 'NEW_FLIGHT_ID'},
                            inplace=True)

    return apds_day_flights


input_filenames = ['daily flights file',
                   'apds flights file',
                   'daily events file',
                   'apds events file']
""" The filenames required by the application. """


def match_apds_trajectories(filenames):

    day_flights_filename = filenames[0]
    apds_flights_filename = filenames[1]

    day_events_filename = filenames[2]
    apds_events_filename = filenames[3]

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
            return errno.EINVAL

    days_date = input_date_strings[0]
    flights_finish_date = input_date_strings[1]
    events_finish_date = input_date_strings[3]

    # Extract the start date string from the filename and validate it
    flights_start_date, _ = split_dual_date(os.path.basename(apds_flights_filename))
    if not is_valid_iso8601_date(flights_start_date):
        log.error('apds flights file: %s, invalid start date: %s',
                  apds_flights_filename, flights_start_date)
        return errno.EINVAL

    # Extract the start date string from the filename and validate it
    events_start_date, _ = split_dual_date(os.path.basename(apds_events_filename))
    if not is_valid_iso8601_date(events_start_date):
        log.error('apds events file: %s, invalid start date: %s',
                  apds_events_filename, events_start_date)
        return errno.EINVAL

    # Ensure that all files are for the same date
    if (input_date_strings[0] != input_date_strings[2]):
        log.error("Daily files are not for the same dates!"
                  " Flights date: %s, Events date: %s",
                  input_date_strings[0], input_date_strings[2])
        return errno.EINVAL

    # Ensure that all files are for the same date
    if (flights_start_date != events_start_date) or \
            (flights_finish_date != events_finish_date):
        log.error("APT files are not for the same dates!"
                  " Flights start date: %s, Events start date: %s",
                  flights_start_date, events_start_date)
        return errno.EINVAL

    # Ensure day is within APT data range
    if not (flights_start_date <= days_date <= flights_finish_date):
        log.error("Daily files are not in APT data range!"
                  " Flights date: %s, APT range: %s to %s",
                  days_date, flights_start_date, flights_finish_date)
        return errno.EINVAL

    ############################################################################
    # Read the data

    # Read days flights into a pandas DataFrame
    day_flights_df = pd.DataFrame()
    try:
        day_flights_df = pd.read_csv(day_flights_filename,
                                     converters={'FLIGHT_ID': lambda x: UUID(x)},
                                     usecols=['FLIGHT_ID', 'CALLSIGN',
                                              'ADEP', 'ADES'],
                                     memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', day_flights_filename)
        return errno.ENOENT

    log.info('daily flights read ok')

    # Read APT flights into a pandas DataFrame
    apds_flights_df = pd.DataFrame()
    try:
        apds_flights_df = pd.read_csv(apds_flights_filename,
                                      usecols=['FLIGHT_ID', 'CALLSIGN',
                                               'ADEP', 'ADES'],
                                      memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', apds_flights_filename)
        return errno.ENOENT

    log.info('apds flights read ok')

    # Read days events into a pandas DataFrame
    day_events_df = pd.DataFrame()
    try:
        day_events_df = pd.read_csv(day_events_filename,
                                    converters={'FLIGHT_ID': lambda x: UUID(x)},
                                    parse_dates=['TIME_SOURCE'],
                                    memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', day_events_filename)
        return errno.ENOENT

    log.info('daily events read ok')

    # Read APT events into a pandas DataFrame
    apds_events_df = pd.DataFrame()
    try:
        apds_events_df = pd.read_csv(apds_events_filename,
                                     parse_dates=['TIME_SOURCE'],
                                     memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', apds_events_filename)
        return errno.ENOENT

    log.info('apds events read ok')

    ############################################################################
    # Match events

    apds_day_flights = match_events(day_flights_df, apds_flights_df,
                                    day_events_df, apds_events_df)

    # Output the days ids
    apds_ids_file = create_matching_ids_filename(APDS, days_date)
    try:
        apds_day_flights.to_csv(apds_ids_file, index=False,
                                columns=['FLIGHT_ID', 'NEW_FLIGHT_ID'])
    except EnvironmentError:
        log.error('could not write file: %s', apds_ids_file)
        return errno.EACCESreturn

    log.info('written file: %s', apds_ids_file)

    log.info('apds matching complete')

    return 0


if __name__ == '__main__':

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        app_name = os.path.basename(sys.argv[0])
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(errno.EINVAL)

    error_code = match_apds_trajectories(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
