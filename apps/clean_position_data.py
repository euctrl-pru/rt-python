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
import csv
import errno
import numpy as np
import pandas as pd
from pru.trajectory_cleaning import find_invalid_positions, \
    DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from pru.trajectory_fields import POSITION_ERROR_FIELDS, \
    ISO8601_DATETIME_FORMAT, BZ2_FILE_EXTENSION, has_bz2_extension
from pru.trajectory_files import RAW, POSITIONS, ERROR_METRICS
from pru.logger import logger

log = logger(__name__)


def clean_position_data(positions_filename, max_speed=DEFAULT_MAX_SPEED,
                        distance_accuracy=DEFAULT_DISTANCE_ACCURACY):

    log.info('positions file: %s', positions_filename)
    log.info('Max speed: %f Knots', max_speed)
    log.info('Distance accuracy: %f NM', distance_accuracy)

    # Read the positions into a pandas DataFrame
    raw_df = pd.DataFrame()
    try:
        raw_df = pd.read_csv(positions_filename, parse_dates=['TIME_SOURCE'],
                             memory_map=True)
        log.info('positions file read ok')

    except EnvironmentError:
        log.error('could not read file: %s', positions_filename)
        sys.exit(errno.ENOENT)

    # A list to hold the error_metrics
    error_metrics = []
    # A numpy array to hold the invalid_positions
    invalid_positions = np.empty(0, dtype=bool)

    raw_df.sort_values(by=['FLIGHT_ID', 'TIME_SOURCE'], inplace=True)
    for flight_id, positions in raw_df.groupby('FLIGHT_ID'):
        try:
            invalid_pos, metrics = find_invalid_positions(positions,
                                                          max_speed=max_speed,
                                                          distance_accuracy=distance_accuracy)
            invalid_positions = np.append(invalid_positions, invalid_pos)
            metrics.insert(0, flight_id)
            error_metrics.append(metrics)

        except (ValueError, TypeError):
            log.exception('find_invalid_positions flight id: %s', flight_id)

    # Extract the valid trajectory positions DataFrame
    valid_positions = raw_df[~invalid_positions]

    log.info('find_invalid_positions finished')

    is_bz2 = has_bz2_extension(positions_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        positions_filename = positions_filename[:-len(BZ2_FILE_EXTENSION)]

    # strip raw_ from the start of the positions_filename
    output_filename = os.path.basename(positions_filename)[len(RAW) + 1:]
    # and write the valid trajectory positions DataFrame as a csv file
    try:
        valid_positions.to_csv(output_filename, index=False,
                               date_format=ISO8601_DATETIME_FORMAT)

        log.info('written file: %s', output_filename)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        sys.exit(errno.EACCES)

    error_metrics_filename = output_filename.replace(POSITIONS, ERROR_METRICS)
    try:
        with open(error_metrics_filename, 'w') as file:
            file.write(POSITION_ERROR_FIELDS)
            writer = csv.writer(file, lineterminator='\n')
            writer.writerows(error_metrics)

    except EnvironmentError:
        log.error('could not write file: %s', error_metrics_filename)
        sys.exit(errno.EACCES)

    log.info('written file: %s', error_metrics_filename)

    log.info('positions cleaned')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: clean_position_data.py <positions_filename>'
              ' [max_speed] [distance_accuracy]')
        sys.exit(errno.EINVAL)

    max_speed = DEFAULT_MAX_SPEED
    if len(sys.argv) >= 3:
        max_speed = float(sys.argv[2])

    distance_accuracy = DEFAULT_DISTANCE_ACCURACY
    if len(sys.argv) >= 4:
        distance_accuracy = float(sys.argv[3])

    error_code = clean_position_data(sys.argv[1], max_speed, distance_accuracy)
    if error_code:
        sys.exit(error_code)
