#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to match Eurocontrol APT data and a days merged trajectories.
"""

import sys
import os
import pandas as pd
from uuid import UUID
from pru.trajectory_fields import read_iso8601_date_string, \
    is_valid_iso8601_date, create_iso8601_csv_filename
from pru.logger import logger


def match_events(day_flights_df, apt_flights_df, day_events_df, apt_events_df):
    """
    Finds common events both data sets.

    It matches on: callsign, departure airport, destination airport, event type,
    and time.

    Returns a pandas DataFrame containing the APT id and the matching days ids
    in 'FLIGHT_ID' and 'NEW_FLIGHT_ID' columns respectively.
    """
    day_flight_events_df = pd.merge(day_flights_df, day_events_df, on='FLIGHT_ID')
    apt_flight_events_df = pd.merge(apt_flights_df, apt_events_df, on='FLIGHT_ID')

    # Find events at the same time in both sets.
    apt_day_flights = pd.merge(apt_flight_events_df, day_flight_events_df,
                               on=['CALLSIGN', 'ADEP', 'ADES',
                                   'EVENT_TYPE', 'TIME_SOURCE'])

    # sort by the apt flight id and drop duplicates (if any)
    apt_day_flights.sort_values(by=['FLIGHT_ID_x'], inplace=True)
    apt_day_flights.drop_duplicates(inplace=True)

    apt_day_flights.rename(index=str, columns={'FLIGHT_ID_x': 'FLIGHT_ID',
                                               'FLIGHT_ID_y': 'NEW_FLIGHT_ID'},
                           inplace=True)

    return apt_day_flights


if __name__ == '__main__':

    input_filenames = ['daily flights file',
                       'apt flights file',
                       'daily events file',
                       'apt events file']
    """ The filenames required by the application. """

    filenames_string = '> <'.join(input_filenames)
    """ A string to inform the user of the required filenames. """

    app_name = os.path.basename(sys.argv[0])
    if len(sys.argv) <= len(input_filenames):
        app_name = os.path.basename(sys.argv[0])
        print('Usage: ' + app_name + ' <' + filenames_string + '>')
        sys.exit(2)

    log = logger(app_name)

    day_flights_filename = sys.argv[1]
    apt_flights_filename = sys.argv[2]

    day_events_filename = sys.argv[3]
    apt_events_filename = sys.argv[4]

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
    flights_finish_date = input_date_strings[1]
    events_finish_date = input_date_strings[3]

    # Extract the start date string from the filename and validate it
    flights_start_date = os.path.basename(apt_flights_filename)[12:22]
    if not is_valid_iso8601_date(flights_start_date):
        log.error('apt flights file: %s, invalid start date: %s',
                  apt_flights_filename, flights_start_date)
        sys.exit(2)

    # Extract the start date string from the filename and validate it
    events_start_date = os.path.basename(apt_events_filename)[11:21]
    if not is_valid_iso8601_date(events_start_date):
        log.error('apt events file: %s, invalid start date: %s',
                  apt_events_filename, events_start_date)
        sys.exit(2)

    # Ensure that all files are for the same date
    if (input_date_strings[0] != input_date_strings[2]):
        log.error("Daily files are not for the same dates!"
                  " Flights date: %s, Events date: %s",
                  input_date_strings[0], input_date_strings[2])
        sys.exit(2)

    # Ensure that all files are for the same date
    if (flights_start_date != events_start_date) or \
            (flights_finish_date != events_finish_date):
        log.error("APT files are not for the same dates!"
                  " Flights start date: %s, Events start date: %s",
                  flights_start_date, events_start_date)
        sys.exit(2)

    # Ensure day is within APT data range
    if not (flights_start_date <= days_date <= flights_finish_date):
        log.error("Daily files are not in APT data range!"
                  " Flights date: %s, APT range: %s to %s",
                  days_date, flights_start_date, flights_finish_date)
        sys.exit(2)

    ############################################################################
    # Read the data

    # Read days flights into a pandas DataFrame
    day_flights_df = pd.DataFrame()
    try:
        day_flights_df = pd.read_csv(day_flights_filename,
                                     converters={'FLIGHT_ID': lambda x: UUID(x)},
                                     usecols=['FLIGHT_ID', 'CALLSIGN',
                                              'ADEP', 'ADES'])
    except EnvironmentError:
        log.error('could not read file: %s', day_flights_filename)
        sys.exit(2)

    log.info('daily flights read ok')

    # Read APT flights into a pandas DataFrame
    apt_flights_df = pd.DataFrame()
    try:
        apt_flights_df = pd.read_csv(apt_flights_filename,
                                     usecols=['FLIGHT_ID', 'CALLSIGN',
                                              'ADEP', 'ADES'])
    except EnvironmentError:
        log.error('could not read file: %s', apt_flights_filename)
        sys.exit(2)

    log.info('apt flights read ok')

    # Read days events into a pandas DataFrame
    day_events_df = pd.DataFrame()
    try:
        day_events_df = pd.read_csv(day_events_filename,
                                    converters={'FLIGHT_ID': lambda x: UUID(x)},
                                    parse_dates=['TIME_SOURCE'])
    except EnvironmentError:
        log.error('could not read file: %s', day_events_filename)
        sys.exit(2)

    log.info('daily events read ok')

    # Read APT events into a pandas DataFrame
    apt_events_df = pd.DataFrame()
    try:
        apt_events_df = pd.read_csv(apt_events_filename,
                                    parse_dates=['TIME_SOURCE'])
    except EnvironmentError:
        log.error('could not read file: %s', apt_events_filename)
        sys.exit(2)

    log.info('apt events read ok')

    ############################################################################
    # Match events

    apt_day_flights = match_events(day_flights_df, apt_flights_df,
                                   day_events_df, apt_events_df)

    # Output the days ids
    apt_ids_file = create_iso8601_csv_filename('apt_matching_ids_', days_date)
    try:
        apt_day_flights.to_csv(apt_ids_file, index=False,
                               columns=['FLIGHT_ID', 'NEW_FLIGHT_ID'])
    except EnvironmentError:
        log.error('could not write file: %s', apt_ids_file)
        sys.exit(2)

    log.info('written file: %s', apt_ids_file)

    log.info('apt matching complete')
