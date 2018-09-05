#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Analyse trajectory position data.
"""

import sys
import os
import csv
import errno
import pandas as pd
from io import StringIO
from pru.trajectory_analysis import analyse_trajectory, DEFAULT_ACROSS_TRACK_TOLERANCE,\
    DEFAULT_MOVING_MEDIAN_SAMPLES, DEFAULT_MOVING_AVERAGE_SAMPLES, \
    DEFAULT_SPEED_MAX_DURATION, MOVING_AVERAGE_SPEED
from pru.trajectory_fields import POSITION_METRICS_FIELDS, BZ2_FILE_EXTENSION, \
    POSITION_FIELDS, CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension
from pru.trajectory_files import POSITIONS, TRAJECTORIES, TRAJ_METRICS
from pru.trajectory_functions import generate_positions
from pru.SmoothedTrajectory import write_SmoothedTrajectories_json_header, \
    SMOOTHED_TRAJECTORY_JSON_FOOTER
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """

POSITION_FIELD_NAMES = POSITION_FIELDS[:-1].split(',')
"""The position fields for the pandas Dataframe."""


def analyse_position_data(filename,
                          across_track_tolerance=DEFAULT_ACROSS_TRACK_TOLERANCE,
                          time_method=MOVING_AVERAGE_SPEED,
                          N=DEFAULT_MOVING_MEDIAN_SAMPLES,
                          M=DEFAULT_MOVING_AVERAGE_SAMPLES,
                          max_duration=DEFAULT_SPEED_MAX_DURATION,
                          logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    Analyse trajectory postions in a positions file.

    Outputs a trajectory file (in JSON format) with "positions" replaced by
    "trajectories" and with the time_method and across_track_tolerance at the
    start of the filename.

    It also outputs a trajectories metrics file in csv format.

    Parameters
    ----------
    filename: a string
        The name of the positions file.

    across_track_tolerance: float
        The maximum across track distance [Nautical Miles],
        default DEFAULT_ACROSS_TRACK_TOLERANCE.

    method: string
        The smoothing method to use: 'mas', 'lm', 'trf' 'dogbox',
        default MOVING_AVERAGE_SPEED.

    N : integer
        The number of samples to consider for the speed moving median filter,
        default DEFAULT_MOVING_MEDIAN_SAMPLES.

    M : integer
        The number of samples to consider for the speed moving average filter,
        default DEFAULT_MOVING_AVERAGE_SAMPLES.

    max_duration: float
        The maximum time between points to smooth when calculating speed [Seconds],
        default DEFAULT_SPEED_MAX_DURATION.

    logging_msg_count: int
        The number of trajectories between logging count messages.
        default DEFAULT_LOGGING_COUNT.

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

    log.info(f'positions file: {filename}')
    log.info(f'across track tolerance: {across_track_tolerance} NM')
    log.info(f'time analysis method: {time_method}')
    if time_method == MOVING_AVERAGE_SPEED:
        log.info(f'moving median samples: {N}')
        log.info(f'moving average samples: {M}')
        log.info(f'speed filter maximum duration: {max_duration}')

    ##########################################################################
    # Create output filenames

    # add the time_method and tolerance to the front of the filename
    tolerance_string = str(across_track_tolerance).replace('.', '')
    positions_filename = '_'.join([time_method, tolerance_string, positions_filename])

    trajectory_filename = positions_filename.replace(POSITIONS, TRAJECTORIES)
    trajectory_filename = trajectory_filename.replace(CSV_FILE_EXTENSION,
                                                      JSON_FILE_EXTENSION)

    traj_metrics_filename = positions_filename.replace(POSITIONS, TRAJ_METRICS)

    ##########################################################################
    # Process the positions

    flights_count = 0
    with open(trajectory_filename, 'w') as output_file, \
            open(traj_metrics_filename, 'w') as metrics_file:
        output_file.write(write_SmoothedTrajectories_json_header(time_method,
                                                                 across_track_tolerance,
                                                                 N, M, max_duration))
        metrics_file.write(POSITION_METRICS_FIELDS)
        metrics_writer = csv.writer(metrics_file, lineterminator='\n')

        try:
            flight_positions = generate_positions(filename)
            for position_lines in flight_positions:

                # Ignore single point trajectories
                if len(position_lines) < 2:
                    continue

                fields = position_lines[0].split(',')
                flight_id = fields[0]
                try:
                    position_string = ''.join(position_lines)
                    positions = pd.read_csv(StringIO(position_string),
                                            header=None, names=POSITION_FIELD_NAMES,
                                            parse_dates=['TIME'])

                    smoothed_traj, quality_metrics = \
                        analyse_trajectory(flight_id, positions,
                                           across_track_tolerance,
                                           time_method, N, M,
                                           max_duration)

                    string_list = smoothed_traj.dumps()
                    if flights_count:
                        # delimit with a comma between flights
                        string_list.insert(0, ', ')
                    output_file.write(''.join(string_list))

                    metrics_writer.writerow(quality_metrics)

                    flights_count += 1
                    if not (flights_count % logging_msg_count):
                        log.info(f'{flights_count} flights analysed')

                except (ValueError, IndexError, TypeError):
                    log.exception(f'analyse_trajectory flight id: {flight_id}')

                except StopIteration:
                    pass

            output_file.write(SMOOTHED_TRAJECTORY_JSON_FOOTER)
            log.info(f'written file: {trajectory_filename}')
            log.info(f'written file: {traj_metrics_filename}')

        except EnvironmentError:
            log.error(f'could not read file: {filename}')
            return errno.ENOENT

    log.info(f'analyse_trajectory finished for {flights_count} flights')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: analyse_position_data.py <positions_filename>'
              ' [across_track_tolerance] [time analysis method]'
              ' [median_filter_samples] [average_filter_samples]'
              ' [speed_max_duration] [logging_msg_count]')
        sys.exit(errno.EINVAL)

    positions_filename = sys.argv[1]

    across_track_tolerance = DEFAULT_ACROSS_TRACK_TOLERANCE
    if len(sys.argv) >= 3:
        try:
            across_track_tolerance = float(sys.argv[2])
        except ValueError:
            log.error(f'invalid across_track_tolerance: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    time_method = MOVING_AVERAGE_SPEED
    if len(sys.argv) >= 4:
        time_method = sys.argv[3]

    N = DEFAULT_MOVING_MEDIAN_SAMPLES
    if len(sys.argv) >= 5:
        try:
            N = int(sys.argv[4])
        except ValueError:
            log.error(f'invalid median_filter_samples: {sys.argv[4]}')
            sys.exit(errno.EINVAL)

    M = DEFAULT_MOVING_AVERAGE_SAMPLES
    if len(sys.argv) >= 6:
        try:
            M = int(sys.argv[5])
        except ValueError:
            log.error(f'invalid average_filter_samples: {sys.argv[5]}')
            sys.exit(errno.EINVAL)

    max_duration = DEFAULT_SPEED_MAX_DURATION
    if len(sys.argv) >= 7:
        try:
            max_duration = float(sys.argv[6])
        except ValueError:
            log.error(f'invalid speed_max_duration: {sys.argv[6]}')
            sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 8:
        logging_msg_count = int(sys.argv[7])

    error_code = analyse_position_data(sys.argv[1], across_track_tolerance,
                                       time_method, N, M, max_duration,
                                       logging_msg_count)
    if error_code:
        sys.exit(error_code)
