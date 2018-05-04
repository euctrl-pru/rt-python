#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Convert IATA airport codes in FR24 ADS-B files to ICAO airport codes.
"""

import sys
import os
import errno
import pandas as pd
from pru.trajectory_fields import is_valid_iso8601_date, read_iso8601_date_string
from pru.trajectory_files import create_flights_filename, FR24, IATA
from pru.logger import logger

log = logger(__name__)

DEFAULT_AIRPORTS_FILENAME = 'airports.csv'
""" The default name of the file containing airport codes. """


def convert_airport_ids(flights_filename,
                        airports_filename=DEFAULT_AIRPORTS_FILENAME):

    # Validate the filename
    filename_start = os.path.basename(flights_filename)[:len(IATA)]
    if filename_start != IATA:
        log.error('File is not an iata_ flights file: %s', flights_filename)
        return errno.EINVAL

    # Extract the date string from the filename and validate it
    flights_date = read_iso8601_date_string(flights_filename)
    if not is_valid_iso8601_date(flights_date):
        log.error('iata fr24 flights file: %s, invalid date: %s',
                  flights_filename, flights_date)
        return errno.EINVAL

    log.info('iata fr24 file: %s', flights_filename)
    log.info('airports file: %s', airports_filename)

    # Read the flights into a pandas DataFrame
    flights_df = pd.DataFrame()
    try:
        flights_df = pd.read_csv(flights_filename, memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', flights_filename)
        return errno.ENOENT

    log.info('flights file read ok')

    # Read the airports into a pandas DataFrame
    airports_df = pd.DataFrame()
    try:
        airports_df = pd.read_csv(airports_filename, memory_map=True)
    except EnvironmentError:
        log.error('could not read file: %s', airports_filename)
        return errno.ENOENT

    log.info('airports file read ok')

    # Create a new dataframe indexed by IATA_AP_CODE, referencing ICAO_AP_CODE
    airport_codes_df = airports_df.set_index('IATA_AP_CODE')['ICAO_AP_CODE']

    # Replace flight IATA airport codes with ICAO airport codes
    flights_df['ADEP'] = flights_df['ADEP'].replace(airport_codes_df)
    flights_df['ADES'] = flights_df['ADES'].replace(airport_codes_df)

    log.info('airport ids converted')

    output_filename = create_flights_filename(FR24, flights_date)
    try:
        flights_df.to_csv(output_filename, index=False)

        log.info('written file: %s', output_filename)
    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    log.info('airports conversion complete')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: convert_airport_ids.py <fr24_flights_filename> [airports_filename]')
        sys.exit(errno.EINVAL)

    flights_filename = sys.argv[1]

    # Get the airports_filename, override the default if necesary
    airports_filename = DEFAULT_AIRPORTS_FILENAME
    if len(sys.argv) >= 3:
        airports_filename = sys.argv[2]

    error_code = convert_airport_ids(flights_filename, airports_filename)
    if error_code:
        sys.exit(error_code)
