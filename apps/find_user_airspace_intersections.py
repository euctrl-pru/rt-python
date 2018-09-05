#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Find trajectory airspace sector intersections.
"""

import sys
import os
import errno
from pru.SmoothedTrajectory import generate_SmoothedTrajectories
from pru.trajectory_user_airspace_intersections import find_trajectory_user_airspace_intersections
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT, has_bz2_extension, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, BZ2_FILE_EXTENSION, AIRSPACE_INTERSECTION_FIELDS
from pru.trajectory_files import TRAJECTORIES, USER_INTERSECTIONS
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def find_user_airspace_intersections(filename, logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    Find intersections between trajectories and user defined airspace volumes.

    Parameters
    ----------
    filename: a string
        The name of a trajectories file.

    logging_msg_count: int
        The number of trajectories between logging count messages.
        default DEFAULT_LOGGING_COUNT.

    Returns
    -------
    An errno error_code if an error occured, zero otherwise.

    """
    log.info(f'trajectories file: {filename}')
    trajectories_filename = os.path.basename(filename)
    is_bz2 = has_bz2_extension(filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the sector intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, USER_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        with open(output_filename, 'w') as file:
            file.write(AIRSPACE_INTERSECTION_FIELDS)

            flights_count = 0
            zeros_count = 0
            smoothed_trajectories = generate_SmoothedTrajectories(filename)
            for smooth_traj in smoothed_trajectories:
                try:
                    flight_id = smooth_traj.flight_id
                    sect_ints = find_trajectory_user_airspace_intersections(smooth_traj)
                    if not sect_ints.empty:
                        sect_ints.to_csv(file, index=False,
                                         header=False, mode='a',
                                         date_format=ISO8601_DATETIME_US_FORMAT)
                    else:
                        zeros_count += 1
                        # log.warn(f'no intersections found with flight: {flight_id}')

                    flights_count += 1
                    if not (flights_count % logging_msg_count):
                        log.info(f'{flights_count} trajectories processed')

                except ValueError:
                    log.exception(f'find_trajectory_user_airspace_intersections id: {flight_id}')

                except StopIteration:
                    pass

            log.info(f'find_user_airspace_intersections finished for {flights_count} trajectories')
            log.info(f'{zeros_count} trajectories had no intersections')

    except EnvironmentError:
        log.error(f'could not write file: {output_filename}')
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_user_airspace_intersections.py <trajectories_filename>'
              ' [logging_msg_count]')
        sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 3:
        logging_msg_count = int(sys.argv[2])

    error_code = find_user_airspace_intersections(sys.argv[1], logging_msg_count)
    if error_code:
        sys.exit(error_code)
