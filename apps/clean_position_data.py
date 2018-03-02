#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Clean trajectory position data.

Removes duplicate points and erroneous positions.
"""

import sys
import os
import numpy as np
import pandas as pd
from pru.trajectory_cleaning import find_invalid_positions, \
    DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from pru.trajectory_fields import POSITION_ERROR_FIELDS, \
    ISO8601_DATETIME_FORMAT, BZ2_FILE_EXTENSION, has_bz2_extension
from pru.logger import logger

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: clean_position_data.py <positions_filename>'
              ' [max_speed] [distance_accuracy]')
        sys.exit(2)

    log = logger(os.path.basename(sys.argv[0]))

    positions_filename = sys.argv[1]

    # The maximum speed between points
    max_speed = DEFAULT_MAX_SPEED
    if len(sys.argv) >= 3:
        max_speed = float(sys.argv[2])

    # Maximum distance between points at the same time
    distance_accuracy = DEFAULT_DISTANCE_ACCURACY
    if len(sys.argv) >= 4:
        distance_accuracy = float(sys.argv[3])

    log.info('positions file: %s', positions_filename)
    log.info('Max speed: %f Knots', max_speed)
    log.info('Distance accuracy: %f NM', distance_accuracy)

    # Read the positions into a pandas DataFrame
    raw_df = pd.DataFrame()
    try:
        raw_df = pd.read_csv(positions_filename, parse_dates=['TIME_SOURCE'])
    except EnvironmentError:
        log.error('could not read file: %s', positions_filename)
        sys.exit(2)
    log.info('positions file read ok')

    # A dict to hold the error_metrics
    error_metrics = {}
    # A numpy array to hold the invalid_positions
    invalid_positions = np.empty(0, dtype=bool)

    raw_df.sort_values(by=['FLIGHT_ID', 'TIME_SOURCE'], inplace=True)
    for flight_id, positions in raw_df.groupby('FLIGHT_ID'):
        invalid_pos, metrics = find_invalid_positions(positions,
                                                      max_speed=max_speed,
                                                      distance_accuracy=distance_accuracy)
        invalid_positions = np.append(invalid_positions, invalid_pos)
        # Output error metrics for all. Use if metrics[0]: just for errors
        error_metrics.setdefault(flight_id, metrics)

    # Extract the valid trajectory positions DataFrame
    valid_positions = raw_df[~invalid_positions]

    log.info('find_invalid_positions finished')

    # And write the valid trajectory positions DataFrame as a csv file
    output_filename = 'clean_' + positions_filename
    is_bz2 = has_bz2_extension(positions_filename)
    try:
        if is_bz2:
            valid_positions.to_csv(output_filename, index=False,
                                   date_format=ISO8601_DATETIME_FORMAT,
                                   compression='bz2')
        else:
            valid_positions.to_csv(output_filename, index=False,
                                   date_format=ISO8601_DATETIME_FORMAT)
    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        sys.exit(2)

    log.info('written file: %s', output_filename)

    quality_filename = 'errors_' + positions_filename
    if is_bz2:  # remove the .bz2 from the end of the filename
        quality_filename = quality_filename[:-len(BZ2_FILE_EXTENSION)]

    try:
        with open(quality_filename, 'w') as file:
            file.write(POSITION_ERROR_FIELDS)
            for key, metrics in sorted(error_metrics.items()):
                print(key, metrics[0], metrics[1], metrics[2], metrics[3], metrics[4],
                      sep=',', file=file)
    except EnvironmentError:
        log.error('could not write file: %s', quality_filename)
        sys.exit(2)

    log.info('written file: %s', quality_filename)

    log.info('positions cleaned')
