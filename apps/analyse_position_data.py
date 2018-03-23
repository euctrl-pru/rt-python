#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Analyse trajectory position data.
"""

import sys
import os
import errno
import pandas as pd
# from pru.horizontal_path_functions import DEFAULT_ACROSS_TRACK_TOLERANCE
from pru.trajectory_analysis import analyse_trajectory, DEFAULT_ACROSS_TRACK_TOLERANCE
from pru.trajectory_fields import read_iso8601_date_string, is_valid_iso8601_date, \
    create_iso8601_csv_filename, POSITION_METRICS_FIELDS
from pru.SmoothedTrajectory import dumps_SmoothedTrajectories
from pru.logger import logger

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: analyse_position_data.py <positions_filename>'
              ' [across_track_tolerance]')
        sys.exit(errno.EINVAL)

    log = logger(os.path.basename(sys.argv[0]))

    positions_filename = sys.argv[1]

    across_track_tolerance = DEFAULT_ACROSS_TRACK_TOLERANCE
    if len(sys.argv) >= 3:
        try:
            across_track_tolerance = float(sys.argv[2])
        except ValueError:
            log.error('invalid across_track_tolerance: %s', sys.argv[2])
            sys.exit(errno.EINVAL)

    positions_date = read_iso8601_date_string(positions_filename)
    if is_valid_iso8601_date(positions_date):
        log.info('positions file: %s', positions_filename)
    else:
        log.error('positions file, invalid date: %s', positions_date)
        sys.exit(errno.EINVAL)

    log.info('Across track tolerance: %f NM', across_track_tolerance)

    raw_df = pd.DataFrame()
    try:
        raw_df = pd.read_csv(positions_filename, parse_dates=['TIME_SOURCE'],
                             usecols=['FLIGHT_ID', 'TIME_SOURCE',
                                      'LAT', 'LON', 'ALT'])
    except EnvironmentError:
        log.error('could not read file: %s', positions_filename)
        sys.exit(errno.ENOENT)
    log.info('positions file read ok')

    # An array to hold the quality_metrics
    quality_metrics = []
    # An array to hold the SmoothedTrajectories
    trajectories = []
    for flight_id, positions in raw_df.groupby('FLIGHT_ID'):
        try:
            smoothed_traj, metrics = analyse_trajectory(flight_id, positions,
                                                        across_track_tolerance)
            trajectories.append(smoothed_traj)
            quality_metrics.append(metrics)
        except (ValueError, TypeError):
            log.exception('analyse_trajectory flight id: %s', flight_id)

    log.info('analyse_trajectory finished')

    trajectory_filename = 'trajectories_' + positions_date + '.json'
    try:
        with open(trajectory_filename, 'w') as file:
            file.write(dumps_SmoothedTrajectories(trajectories))
    except EnvironmentError:
        log.error('could not write file: %s', trajectory_filename)
        sys.exit(errno.EACCES)

    log.info('written file: %s', trajectory_filename)

    quality_filename = create_iso8601_csv_filename('traj_metrics_', positions_date)
    try:
        with open(quality_filename, 'w') as file:
            file.write(POSITION_METRICS_FIELDS)
            for metrics in quality_metrics:
                print(metrics[0], metrics[1], metrics[2], metrics[3],
                      metrics[4], metrics[5], metrics[6], sep=',', file=file)
    except EnvironmentError:
        log.error('could not write file: %s', quality_filename)
        sys.exit(errno.EACCES)

    log.info('written file: %s', quality_filename)

    log.info('positions analysed')
