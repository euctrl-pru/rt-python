#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Convert IATA airport codes in FR24 ADS-B files to ICAO airport codes.
"""

import sys
import os
import pandas as pd
from pru.trajectory_fields import has_bz2_extension
from pru.logger import logger

IATA_STRING = 'iata_'
""" The string at the start of flight files with IATA airport codes. """

DEFAULT_AIRPORTS_FILENAME = 'airports.csv'
""" The default name of the file containing airport codes. """

if len(sys.argv) < 2:
    print('Usage: convert_airport_ids.py <fr24_flights_filename> [airports_filename]')
    sys.exit(2)

log = logger(os.path.basename(sys.argv[0]))

flights_filename = sys.argv[1]
is_bz2 = has_bz2_extension(flights_filename)

# Validate the filename
filename_start = os.path.basename(flights_filename)[:5]
if filename_start != IATA_STRING:
    log.error('File is not an iata_ flights file: %s', flights_filename)
    sys.exit(2)

log.info('fr24 file: %s', flights_filename)

# Get the airports_filename, override the default if necesary
airports_filename = DEFAULT_AIRPORTS_FILENAME
if len(sys.argv) >= 3:
    airports_filename = sys.argv[2]

log.info('airports file: %s', airports_filename)

# Read the flights into a pandas DataFrame
flights_df = pd.DataFrame()
try:
    flights_df = pd.read_csv(flights_filename)
except EnvironmentError:
    log.error('could not read file: %s', flights_filename)
    sys.exit(2)

log.info('flights file read ok')

# Read the airports into a pandas DataFrame
airports_df = pd.DataFrame()
try:
    airports_df = pd.read_csv(airports_filename)
except EnvironmentError:
    log.error('could not read file: %s', airports_filename)
    sys.exit(2)

log.info('airports file read ok')

# Create a new dataframe indexed by IATA_AP_CODE, referencing ICAO_AP_CODE
airport_codes_df = airports_df.set_index('IATA_AP_CODE')['ICAO_AP_CODE']

# Replace flight IATA airport codes with ICAO airport codes
flights_df['ADEP'] = flights_df['ADEP'].replace(airport_codes_df)
flights_df['ADES'] = flights_df['ADES'].replace(airport_codes_df)

log.info('airport ids converted')

# strip IATA_STRING from the start of the output filename
output_filename = flights_filename[5:]
try:
    # Ensure output file is in same format as input file
    if is_bz2:
        flights_df.to_csv(output_filename, index=False, compression='bz2')
    else:
        flights_df.to_csv(output_filename, index=False)
except EnvironmentError:
    log.error('could not write file: %s', output_filename)
    sys.exit(2)

log.info('written file: %s', output_filename)

log.info('airports conversion complete')
