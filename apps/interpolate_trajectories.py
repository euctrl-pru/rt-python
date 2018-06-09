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
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT, BZ2_FILE_EXTENSION, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension, POSITION_FIELDS
from pru.trajectory_files import TRAJECTORIES, REF_POSITIONS
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of analysed flights between each log message. """


def interpolate_trajectories(filename,
                             straight_interval=DEFAULT_STRAIGHT_INTERVAL,
                             turn_interval=DEFAULT_TURN_INTERVAL,
                             logging_msg_count=DEFAULT_LOGGING_COUNT):

    log.info('trajectories file: %s', filename)
    log.info('Straight interval: %f Seconds', straight_interval)
    log.info('Turn interval: %f Seconds', turn_interval)

    is_bz2 = has_bz2_extension(filename)

    smoothed_trajectories = []
    # Read the trajectories file into smoothed_trajectories
    try:

        with bz2.open(filename, 'rt',  newline="") if (is_bz2) else \
                open(filename, 'r') as file:
            json_data = json.loads(file.read())
            smoothed_trajectories = loads_SmoothedTrajectories(json_data)
    except EnvironmentError:
        log.error('could not read file: %s', filename)
        return errno.ENOENT

    trajectories_filename = os.path.basename(filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    output_filename = trajectories_filename.replace(TRAJECTORIES, REF_POSITIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        file = open(output_filename, 'w')
        file.write(POSITION_FIELDS)

        # Interpolate the smoothed_trajectories into reference_positions
        flights_count = 0
        for smooth_traj in smoothed_trajectories:
            try:
                flight_id = smooth_traj.flight_id
                ref_traj = interpolate_trajectory_positions(smooth_traj,
                                                            straight_interval, turn_interval)
                ref_traj.to_csv(file, index=False, header=False, mode='a',
                                date_format=ISO8601_DATETIME_US_FORMAT)

                flights_count += 1
                if not (flights_count % logging_msg_count):
                    log.info('%i trajectories interpolated', flights_count)

            except ValueError:
                log.exception('interpolate_trajectory id: %s', flight_id)

        file.close()

        log.info('Finished interpolating %i trajectories!', flights_count)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: interpolate_trajectories.py <trajectories_filename>'
              ' [straight_interval] [turn_interval] [logging_msg_count]')
        sys.exit(errno.EINVAL)

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

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 5:
        logging_msg_count = int(sys.argv[6])

    error_code = interpolate_trajectories(sys.argv[1],
                                          straight_interval, turn_interval,
                                          logging_msg_count)
    if error_code:
        sys.exit(error_code)
