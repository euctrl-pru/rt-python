#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Find trajectory airspace sector intersections.
"""

import sys
import bz2
import os
import errno
import pandas as pd
import json
from pru.SmoothedTrajectory import loads_SmoothedTrajectories
from pru.trajectory_user_airspace_intersections import find_trajectory_user_airspace_intersections
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT, has_bz2_extension, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, BZ2_FILE_EXTENSION, AIRSPACE_INTERSECTION_FIELDS
from pru.trajectory_files import TRAJECTORIES, USER_INTERSECTIONS
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def find_user_airspace_intersections(filename, logging_msg_count=DEFAULT_LOGGING_COUNT):

    is_bz2 = has_bz2_extension(filename)

    smoothed_trajectories = []
    # Read the trajectories file into smoothed_trajectories
    try:
        with bz2.open(filename, 'rt',  newline="") if (is_bz2) else \
                open(filename, 'r') as file:
            json_data = json.loads(file.read())
            smoothed_trajectories = loads_SmoothedTrajectories(json_data)

        log.info('find_user_airspace_intersections read file: %s', filename)

    except EnvironmentError:
        log.error('could not read file: %s', filename)
        return errno.ENOENT

    trajectories_filename = os.path.basename(filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the sector intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, USER_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        file = open(output_filename, 'w')
        file.write(AIRSPACE_INTERSECTION_FIELDS)

        flights_count = 0
        for smooth_traj in smoothed_trajectories:
            try:
                flight_id = smooth_traj.flight_id
                sect_ints = find_trajectory_user_airspace_intersections(smooth_traj)
                if sect_ints.empty:
                    log.warn('no intersections found with flight: %s', flight_id)
                else:
                    sect_ints.to_csv(file, index=False,
                                     header=False, mode='a',
                                     date_format=ISO8601_DATETIME_US_FORMAT)

                flights_count += 1
                if not (flights_count % logging_msg_count):
                    log.info('%i trajectories processed', flights_count)

            except ValueError:
                log.exception('find_trajectory_user_airspace_intersections id: %s', flight_id)

        file.close()

        log.info('find_user_airspace_intersections finished for %i trajectories!',
                 flights_count)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_user_airspace_intersections.py <trajectories_filename>'
              ' [logging_msg_count]')
        sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 3:
        logging_msg_count = int(sys.argv[4])

    error_code = find_user_airspace_intersections(sys.argv[1], logging_msg_count)
    if error_code:
        sys.exit(error_code)
