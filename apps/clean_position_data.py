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
import pandas as pd
from io import StringIO
from pru.trajectory_cleaning import find_invalid_positions, \
    DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from pru.trajectory_fields import POSITION_FIELDS, POSITION_ERROR_FIELDS, \
    ISO8601_DATETIME_FORMAT, BZ2_FILE_EXTENSION, has_bz2_extension, \
    CSV_FILE_EXTENSION
from pru.trajectory_files import RAW, POSITIONS, ERROR_METRICS
from pru.trajectory_functions import generate_positions
from pru.logger import logger

log = logger(__name__)

POSITION_FIELD_NAMES = POSITION_FIELDS[:-1].split(',')
"""The position fields for the pandas Dataframe."""


def clean_position_data(filename, max_speed=DEFAULT_MAX_SPEED,
                        distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Identify and remove invalid postions in a positions file.

    Outputs a positions file with "raw_" stripped from the start of the
    filename and an error metrics file.

    Parameters
    ----------
    filename: a string
        The name of the raw positions file.

    max_speed: float
        The maximum speed betwen valid positions [Knots].
        Default: DEFAULT_MAX_SPEED.

    distance_accuracy: float
        The accuracy of the positions [Nautical Miles].

    Returns
    -------
    An errno error_code if an error occured, zero otherwise.

    """
    positions_filename = os.path.basename(filename)
    is_bz2 = has_bz2_extension(positions_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        positions_filename = positions_filename[:-len(BZ2_FILE_EXTENSION)]

    if positions_filename[-len(CSV_FILE_EXTENSION):] != CSV_FILE_EXTENSION:
        log.error(f'Invalid file type: {positions_filename}, must be a CSV file.')
        return errno.EINVAL

    log.info(f'positions file: {positions_filename}')
    log.info(f'Max speed: {max_speed} Knots')
    log.info(f'Distance accuracy: {distance_accuracy} NM')

    ##########################################################################
    # Create output filenames

    # strip raw_ from the start of the positions_filename
    output_filename = os.path.basename(positions_filename)[len(RAW) + 1:]

    error_metrics_filename = output_filename.replace(POSITIONS, ERROR_METRICS)

    ##########################################################################
    # Process the positions

    flights_count = 0
    with open(output_filename, 'w') as output_file, \
            open(error_metrics_filename, 'w') as error_file:
        output_file.write(POSITION_FIELDS)

        error_file.write(POSITION_ERROR_FIELDS)
        error_writer = csv.writer(error_file, lineterminator='\n')

        try:
            flight_positions = generate_positions(positions_filename)
            for position_lines in flight_positions:
                fields = position_lines[0].split(',')
                flight_id = fields[0]
                try:
                    position_string = ''.join(position_lines)
                    positions = pd.read_csv(StringIO(position_string),
                                            header=None, names=POSITION_FIELD_NAMES,
                                            parse_dates=['TIME'])

                    invalid_positions, error_metrics = \
                        find_invalid_positions(positions,
                                               max_speed=max_speed,
                                               distance_accuracy=distance_accuracy)

                    valid_positions = positions[~invalid_positions]
                    valid_positions.to_csv(output_file, index=False,
                                           header=False, mode='a',
                                           date_format=ISO8601_DATETIME_FORMAT)

                    error_metrics.insert(0, flight_id)
                    error_writer.writerow(error_metrics)

                    flights_count += 1

                except (ValueError, TypeError):
                    log.exception(f'find_invalid_positions flight id: {flight_id}')

                except StopIteration:
                    pass

            log.info(f'written file: {output_filename}')
            log.info(f'written file: {error_metrics_filename}')

        except EnvironmentError:
            log.error(f'could not read file: {positions_filename}')
            return errno.ENOENT

    log.info(f'positions cleaned for {flights_count} flights')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: clean_position_data.py <positions_filename>'
              ' [max_speed] [distance_accuracy]')
        sys.exit(errno.EINVAL)

    max_speed = DEFAULT_MAX_SPEED
    if len(sys.argv) >= 3:
        try:
            max_speed = float(sys.argv[2])
        except ValueError:
            log.error(f'invalid max_speed: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    distance_accuracy = DEFAULT_DISTANCE_ACCURACY
    if len(sys.argv) >= 4:
        try:
            distance_accuracy = float(sys.argv[3])
        except ValueError:
            log.error(f'invalid distance_accuracy: { sys.argv[3]}')
            sys.exit(errno.EINVAL)

    error_code = clean_position_data(sys.argv[1], max_speed, distance_accuracy)
    if error_code:
        sys.exit(error_code)
