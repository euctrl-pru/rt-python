#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Interpolate trajectory position data.
"""

import sys
import bz2
import os
import errno
import pandas as pd
import json
from pru.SmoothedTrajectory import loads_SmoothedTrajectories
from pru.trajectory_interpolation import interpolate_trajectory_positions, \
    DEFAULT_STRAIGHT_INTERVAL, DEFAULT_TURN_INTERVAL
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT, has_bz2_extension, \
    read_iso8601_date_string, is_valid_iso8601_date, create_iso8601_csv_filename
from pru.logger import logger

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: interpolate_trajectories.py <trajectories_filename>'
              ' [straight_interval] [turn_interval]')
        sys.exit(errno.EINVAL)

    log = logger(os.path.basename(sys.argv[0]))

    trajectories_filename = sys.argv[1]

    straight_interval = DEFAULT_STRAIGHT_INTERVAL
    if len(sys.argv) >= 3:
        try:
            straight_interval = float(sys.argv[2])
        except ValueError:
            log.error('invalid straight_interval: %s', sys.argv[2])
            sys.exit(errno.EINVAL)

    turn_interval = DEFAULT_TURN_INTERVAL
    if len(sys.argv) >= 4:
        try:
            turn_interval = float(sys.argv[3])
        except ValueError:
            log.error('invalid turn_interval: %s', sys.argv[3])
            sys.exit(errno.EINVAL)

    trajectories_date = read_iso8601_date_string(trajectories_filename,
                                                 is_json=True)
    if is_valid_iso8601_date(trajectories_date):
        log.info('trajectories file: %s', trajectories_filename)
    else:
        log.error('trajectories file, invalid date: %s', trajectories_date)
        sys.exit(errno.EINVAL)

    log.info('Straight interval: %f Seconds', straight_interval)
    log.info('Turn interval: %f Seconds', turn_interval)

    smoothed_trajectories = []
    # Read the trajectories file into smoothed_trajectories
    try:
        is_bz2 = has_bz2_extension(trajectories_filename)
        with bz2.open(trajectories_filename, 'rt',  newline="") if (is_bz2) else \
                open(trajectories_filename, 'r') as file:
            json_data = json.loads(file.read())
            smoothed_trajectories = loads_SmoothedTrajectories(json_data)
    except EnvironmentError:
        log.error('could not read file: %s', trajectories_filename)
        sys.exit(errno.ENOENT)

    reference_positions = pd.DataFrame()
    # Interpolate the smoothed_trajectories into reference_positions
    for smooth_traj in smoothed_trajectories:
        try:
            flight_id = smooth_traj.flight_id
            ref_traj = interpolate_trajectory_positions(smooth_traj,
                                                        straight_interval, turn_interval)
            reference_positions = pd.concat([reference_positions, ref_traj],
                                            ignore_index=True)
        except ValueError:
            log.exception('interpolate_trajectory id: %s', flight_id)

    output_filename = create_iso8601_csv_filename('ref_positions_',
                                                  trajectories_date)
    # Write the reference_positions into a csv file with output_filename
    try:
        reference_positions.to_csv(output_filename, index=False,
                                   date_format=ISO8601_DATETIME_US_FORMAT)
    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        sys.exit(errno.EACCES)

    log.info('written file: %s', output_filename)

    log.info('trajectories created')
