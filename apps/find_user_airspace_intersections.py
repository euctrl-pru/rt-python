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
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, BZ2_FILE_EXTENSION
from pru.trajectory_files import TRAJECTORIES, USER_INTERSECTIONS
from pru.logger import logger

log = logger(__name__)


def find_user_airspace_intersections(filename):

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

    sector_intersections = pd.DataFrame()
    for smooth_traj in smoothed_trajectories:
        try:
            flight_id = smooth_traj.flight_id
            sect_ints = find_trajectory_user_airspace_intersections(smooth_traj)
            if sect_ints.empty:
                log.warn('no intersections found with flight: %s', flight_id)
            else:
                sector_intersections = pd.concat([sector_intersections, sect_ints],
                                                 ignore_index=True)
        except ValueError:
            log.exception('find_trajectory_user_airspace_intersections id: %s', flight_id)

    log.info('user airspace intersections found')

    trajectories_filename = os.path.basename(filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the sector intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, USER_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        sector_intersections.to_csv(output_filename, index=False,
                                    date_format=ISO8601_DATETIME_US_FORMAT)
        log.info('written file: %s', output_filename)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    log.info('find_user_airspace_intersections finished')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_user_airspace_intersections.py <trajectories_filename>')
        sys.exit(errno.EINVAL)

    error_code = find_user_airspace_intersections(sys.argv[1])
    if error_code:
        sys.exit(error_code)
