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
from pru.trajectory_analysis import analyse_trajectory, DEFAULT_ACROSS_TRACK_TOLERANCE,\
    MOVING_AVERAGE_SPEED
from pru.trajectory_fields import POSITION_METRICS_FIELDS, BZ2_FILE_EXTENSION, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension
from pru.trajectory_files import POSITIONS, TRAJECTORIES, TRAJ_METRICS
from pru.SmoothedTrajectory import dumps_SmoothedTrajectories
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of analysed flights between each log message. """


def analyse_position_data(filename,
                          across_track_tolerance=DEFAULT_ACROSS_TRACK_TOLERANCE,
                          time_method=MOVING_AVERAGE_SPEED,
                          logging_msg_count=DEFAULT_LOGGING_COUNT):

    log.info('positions file: %s', filename)
    log.info('across track tolerance: %f NM', across_track_tolerance)
    log.info('time analysis method: %s', time_method)

    raw_df = pd.DataFrame()
    try:
        raw_df = pd.read_csv(filename, parse_dates=['TIME'],
                             usecols=['FLIGHT_ID', 'TIME',
                                      'LAT', 'LON', 'ALT'],
                             memory_map=True)
        log.info('positions file read ok')

    except EnvironmentError:
        log.error('could not read file: %s', filename)
        return errno.ENOENT

    # An array to hold the quality_metrics
    quality_metrics = []
    # An array to hold the SmoothedTrajectories
    trajectories = []
    flights_count = 0
    for flight_id, positions in raw_df.groupby('FLIGHT_ID'):
        try:
            smoothed_traj, metrics = analyse_trajectory(flight_id, positions,
                                                        across_track_tolerance,
                                                        time_method)
            trajectories.append(smoothed_traj)
            quality_metrics.append(metrics)

            flights_count += 1
            if not (flights_count % logging_msg_count):
                log.info('%i flights analysed', flights_count)

        except (ValueError, IndexError, TypeError):
            log.exception('analyse_trajectory flight id: %s', flight_id)

    log.info('analyse_trajectory finished for %s flights', flights_count)

    positions_filename = os.path.basename(filename)
    is_bz2 = has_bz2_extension(positions_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        positions_filename = positions_filename[:-len(BZ2_FILE_EXTENSION)]

    # add the time_method and tolerance to the front of the filename
    tolerance_string = str(across_track_tolerance).replace('.', '')
    positions_filename = '_'.join([time_method, tolerance_string, positions_filename])

    trajectory_filename = positions_filename.replace(POSITIONS, TRAJECTORIES)
    trajectory_filename = trajectory_filename.replace(CSV_FILE_EXTENSION,
                                                      JSON_FILE_EXTENSION)

    try:
        with open(trajectory_filename, 'w') as file:
            file.write(dumps_SmoothedTrajectories(trajectories, time_method,
                                                  across_track_tolerance))
    except EnvironmentError:
        log.error('could not write file: %s', trajectory_filename)
        return errno.EACCES

    log.info('written file: %s', trajectory_filename)

    traj_metrics_filename = positions_filename.replace(POSITIONS, TRAJ_METRICS)
    try:
        with open(traj_metrics_filename, 'w') as file:
            file.write(POSITION_METRICS_FIELDS)
            writer = csv.writer(file, lineterminator='\n')
            writer.writerows(quality_metrics)

    except EnvironmentError:
        log.error('could not write file: %s', traj_metrics_filename)
        return errno.EACCES

    log.info('written file: %s', traj_metrics_filename)

    log.info('positions analysed')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: analyse_position_data.py <positions_filename>'
              ' [across_track_tolerance] [time analysis method] [logging_msg_count]')
        sys.exit(errno.EINVAL)

    positions_filename = sys.argv[1]

    across_track_tolerance = DEFAULT_ACROSS_TRACK_TOLERANCE
    if len(sys.argv) >= 3:
        try:
            across_track_tolerance = float(sys.argv[2])
        except ValueError:
            log.error('invalid across_track_tolerance: %s', sys.argv[2])
            sys.exit(errno.EINVAL)

    time_method = MOVING_AVERAGE_SPEED
    if len(sys.argv) >= 4:
        time_method = sys.argv[3]

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 5:
        logging_msg_count = int(sys.argv[4])

    error_code = analyse_position_data(sys.argv[1], across_track_tolerance,
                                       time_method, logging_msg_count)
    if error_code:
        sys.exit(error_code)
