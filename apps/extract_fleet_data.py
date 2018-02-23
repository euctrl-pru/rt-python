#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Extract Aircraft: Registration, Address and Type information from
(converted) FR24 ADS-B flight files.
"""

import sys
import os
import pandas as pd
from pru.trajectory_fields import \
    iso8601_date_parser, read_iso8601_date_string, create_iso8601_csv_filename
from pru.logger import logger

if len(sys.argv) < 2:
    print('Usage: extract_fleet_data.py <flights_filename>')
    sys.exit(2)

log = logger(os.path.basename(sys.argv[0]))

flights_filename = sys.argv[1]

# Extract the date string from the filename and validate it
flights_date = read_iso8601_date_string(flights_filename)
try:
    iso8601_date_parser(flights_date)
except ValueError:
    log.error('fr24 flights file: %s, invalid date: %s',
              flights_filename, flights_date)
    sys.exit(2)

log.info('fr24 flights file: %s', flights_filename)

# Read the flights into a pandas DataFrame
flights_df = pd.DataFrame()
try:
    flights_df = pd.read_csv(flights_filename,
                             usecols=['AIRCRAFT_REG', 'AIRCRAFT_TYPE',
                                      'AIRCRAFT_ADDRESS', 'PERIOD_START'])
except EnvironmentError:
    log.error('could not read file: %s', flights_filename)
    sys.exit(2)

log.info('flights file read ok')

# Get the rows with non-null AIRCRAFT_REG fields
valid_reg_df = flights_df.loc[flights_df['AIRCRAFT_REG'].notnull()]

# Create a fleet pandas DataFrame with rows sorted by AIRCRAFT_REG then PERIOD_START
# Remove rows with duplicate: AIRCRAFT_REG, AIRCRAFT_TYPE & AIRCRAFT_ADDRESS
fleet_df = valid_reg_df.sort_values(by=['AIRCRAFT_REG', 'PERIOD_START'])
fleet_df.drop_duplicates(subset=['AIRCRAFT_REG', 'AIRCRAFT_TYPE', 'AIRCRAFT_ADDRESS'],
                         inplace=True)

# Output the fleet DataFrame to a '.csv file
output_filename = create_iso8601_csv_filename('fleet_data_', flights_date)
try:
    fleet_df.to_csv(output_filename, index=False)
except EnvironmentError:
    log.error('could not write file: %s', output_filename)
    sys.exit(2)

log.info('written file: %s', output_filename)
log.info('fleet data extraction complete')
