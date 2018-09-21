#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Interpolate trajectory position data.
"""

import sys
import os
import errno
from pru.SmoothedTrajectory import generate_SmoothedTrajectories
from pru.trajectory_interpolation import interpolate_trajectory_positions, \
    DEFAULT_STRAIGHT_INTERVAL, DEFAULT_TURN_INTERVAL
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT, BZ2_FILE_EXTENSION, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension, POSITION_FIELDS
from pru.trajectory_files import TRAJECTORIES, SYNTH_POSITIONS
from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def interpolate_trajectories(filename,
                             straight_interval=DEFAULT_STRAIGHT_INTERVAL,
                             turn_interval=DEFAULT_TURN_INTERVAL,
                             logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    Interpoates trajectory postions in a trajectories file.

    Outputs a postions file (in CSV format) with "trajectories" replaced by
    "ref_positions" in the filename.

    Parameters
    ----------
    filename: a string
        The name of the trajectories JSON file.

    straight_interval: float
        The time between positions along a straight leg [Seconds],
        default DEFAULT_STRAIGHT_INTERVAL.

    turn_interval: float
        The time between positions while turning [Seconds],
        default DEFAULT_TURN_INTERVAL.

    logging_msg_count: int
        The number of trajectories between logging count messages.
        default DEFAULT_LOGGING_COUNT.

    """
    trajectories_filename = os.path.basename(filename)
    is_bz2 = has_bz2_extension(filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    if trajectories_filename[-len(JSON_FILE_EXTENSION):] != JSON_FILE_EXTENSION:
        log.error(f'Invalid file type: {trajectories_filename}, must be a JSON file.')
        return errno.EINVAL

    log.info(f'trajectories file: {filename}')
    log.info(f'Straight interval: {straight_interval} seconds')
    log.info(f'Turn interval: {turn_interval} seconds')

    output_filename = trajectories_filename.replace(TRAJECTORIES, SYNTH_POSITIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        with open(output_filename, 'w') as file:
            file.write(POSITION_FIELDS)

            # Interpolate the smoothed_trajectories into reference_positions
            flights_count = 0
            smoothed_trajectories = generate_SmoothedTrajectories(filename)
            for smooth_traj in smoothed_trajectories:
                try:
                    flight_id = smooth_traj.flight_id
                    ref_traj = interpolate_trajectory_positions(smooth_traj,
                                                                straight_interval, turn_interval)
                    ref_traj.to_csv(file, index=False, header=False, mode='a',
                                    date_format=ISO8601_DATETIME_US_FORMAT)

                    flights_count += 1
                    if not (flights_count % logging_msg_count):
                        log.info(f'{flights_count} trajectories interpolated')

                except ValueError:
                    log.exception(f'interpolate_trajectory flight id: {flight_id}')

                except StopIteration:
                    pass

            log.info(f'Finished interpolating {flights_count} trajectories.')

    except EnvironmentError:
        log.error(f'could not write file: {output_filename}')
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
            log.error(f'invalid straight_interval: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    turn_interval = DEFAULT_TURN_INTERVAL
    if len(sys.argv) >= 4:
        try:
            turn_interval = float(sys.argv[3])
        except ValueError:
            log.error(f'invalid turn_interval: { sys.argv[3]}')
            sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 5:
        logging_msg_count = int(sys.argv[4])

    error_code = interpolate_trajectories(sys.argv[1],
                                          straight_interval, turn_interval,
                                          logging_msg_count)
    if error_code:
        sys.exit(error_code)
