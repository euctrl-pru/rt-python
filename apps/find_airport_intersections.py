#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Find trajectory airport intersections.
"""

import sys
import bz2
import os
import errno
import pandas as pd
import json
from pru.SmoothedTrajectory import loads_SmoothedTrajectories
from pru.trajectory_airport_intersections import find_airport_intersection, \
    DEFAULT_RADIUS
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT,  BZ2_FILE_EXTENSION, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension, \
    read_iso8601_date_string, is_valid_iso8601_date, AIRPORT_INTERSECTION_FIELDS
from pru.trajectory_files import TRAJECTORIES, AIRPORT_INTERSECTIONS
from pru.logger import logger


log = logger(__name__)

AIRPORT_NAME_LENGTH = 4
""" The length of an airport name. """

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def find_airport_intersections(flights_filename, trajectories_filename,
                               radius=DEFAULT_RADIUS,
                               logging_msg_count=DEFAULT_LOGGING_COUNT):

    # Extract the date string from the filename and validate it
    flights_date = read_iso8601_date_string(flights_filename)
    if is_valid_iso8601_date(flights_date):
        log.info('flights file: %s', flights_filename)
    else:
        log.error('flights file: %s, invalid date: %s',
                  flights_filename, flights_date)
        return errno.EINVAL

    trajectories_date = read_iso8601_date_string(trajectories_filename,
                                                 is_json=True)
    if is_valid_iso8601_date(trajectories_date):
        log.info('trajectories file: %s', trajectories_filename)
    else:
        log.error('trajectories file, invalid date: %s', trajectories_date)
        return errno.EINVAL

    if flights_date != trajectories_date:
        log.error('Files are not for the same date! Flights date: %s, trajectories date: %s',
                  flights_date, trajectories_date)
        return errno.EINVAL

    log.info('flights file: %s', flights_filename)
    log.info('trajectories file: %s', trajectories_filename)
    log.info('radius: %f NM', radius)

    flights_df = pd.DataFrame()
    try:
        flights_df = pd.read_csv(flights_filename,
                                 usecols=['FLIGHT_ID', 'ADEP', 'ADES'],
                                 index_col='FLIGHT_ID',
                                 memory_map=True)

        log.info('flights read ok')
    except EnvironmentError:
        log.error('could not read file: %s', flights_filename)
        return errno.ENOENT

    is_bz2 = has_bz2_extension(trajectories_filename)

    smoothed_trajectories = []
    # Read the trajectories file into smoothed_trajectories
    try:
        with bz2.open(trajectories_filename, 'rt',  newline="") if (is_bz2) else \
                open(trajectories_filename, 'r') as file:
            json_data = json.loads(file.read())
            smoothed_trajectories = loads_SmoothedTrajectories(json_data)
    except EnvironmentError:
        log.error('could not read file: %s', trajectories_filename)
        return errno.ENOENT

    trajectories_filename = os.path.basename(trajectories_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the airport_intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, AIRPORT_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        file = open(output_filename, 'w')
        file.write(AIRPORT_INTERSECTION_FIELDS)

        flights_count = 0
        for smooth_traj in smoothed_trajectories:
            try:
                flight_id = smooth_traj.flight_id
                if flight_id in flights_df.index:

                    departure = str(flights_df.loc[flight_id, 'ADEP'])
                    if len(departure) == AIRPORT_NAME_LENGTH:
                        dep_intersection = find_airport_intersection(smooth_traj,
                                                                     departure,
                                                                     radius, False)
                        if not dep_intersection.empty:
                            dep_intersection.to_csv(file, index=False,
                                                    header=False, mode='a',
                                                    date_format=ISO8601_DATETIME_US_FORMAT)

                    destination = str(flights_df.loc[flight_id, 'ADES'])
                    if len(destination) == AIRPORT_NAME_LENGTH:
                        dest_intersection = find_airport_intersection(smooth_traj,
                                                                      destination,
                                                                      radius, True)
                        if not dest_intersection.empty:
                            dest_intersection.to_csv(file, index=False,
                                                     header=False, mode='a',
                                                     date_format=ISO8601_DATETIME_US_FORMAT)

                    flights_count += 1
                    if not (flights_count % logging_msg_count):
                        log.info('%i trajectories processed', flights_count)

            except ValueError:
                log.exception('find_airport_intersections id: %s', flight_id)

        file.close()

        log.info('find_airport_intersections finished for %i trajectories!',
                 flights_count)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: find_airport_intersections.py <flights_filename>'
              ' <trajectories_filename> [radius] [logging_msg_count]')
        sys.exit(errno.EINVAL)

    radius = DEFAULT_RADIUS
    if len(sys.argv) >= 4:
        try:
            radius = float(sys.argv[3])
        except ValueError:
            log.error('invalid radius: %s', sys.argv[3])
            sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 5:
        logging_msg_count = int(sys.argv[6])

    error_code = find_airport_intersections(sys.argv[1], sys.argv[2],
                                            radius, logging_msg_count)
    if error_code:
        sys.exit(error_code)
