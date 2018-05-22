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
    read_iso8601_date_string, is_valid_iso8601_date
from pru.trajectory_files import TRAJECTORIES, AIRPORT_INTERSECTIONS
from pru.logger import logger


log = logger(__name__)


def find_airport_intersections(flights_filename, trajectories_filename,
                               radius=DEFAULT_RADIUS):

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

    airport_intersections = pd.DataFrame()
    for smooth_traj in smoothed_trajectories:
        try:
            # TODO this should NOT need to be cast!
            flight_id = int(smooth_traj.flight_id)
            if flight_id in flights_df.index:

                departure = flights_df.loc[flight_id, 'ADEP']
                if departure:  # TODO test if an airport we're interested in
                    dep_intersection = find_airport_intersection(smooth_traj,
                                                                 departure,
                                                                 radius, False)
                    airport_intersections = pd.concat([airport_intersections,
                                                       dep_intersection],
                                                      ignore_index=True)

                destination = flights_df.loc[flight_id, 'ADES']
                if destination:  # TODO test if an airport we're interested in
                    dest_intersection = find_airport_intersection(smooth_traj,
                                                                  destination,
                                                                  radius, True)
                    airport_intersections = pd.concat([airport_intersections,
                                                       dest_intersection],
                                                      ignore_index=True)

        except ValueError:
            log.exception('find_airport_intersections id: %s', flight_id)

    trajectories_filename = os.path.basename(trajectories_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the airport_intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, AIRPORT_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        airport_intersections.to_csv(output_filename, index=False,
                                     date_format=ISO8601_DATETIME_US_FORMAT)
        log.info('written file: %s', output_filename)

    except EnvironmentError:
        log.error('could not write file: %s', output_filename)
        return errno.EACCES

    log.info('airport intersections found')

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: find_airport_intersections.py <flights_filename>'
              ' <trajectories_filename> [radius]')
        sys.exit(errno.EINVAL)

    radius = DEFAULT_RADIUS
    if len(sys.argv) >= 4:
        try:
            radius = float(sys.argv[3])
        except ValueError:
            log.error('invalid radius: %s', sys.argv[3])
            sys.exit(errno.EINVAL)

    error_code = find_airport_intersections(sys.argv[1], sys.argv[2], radius)
    if error_code:
        sys.exit(error_code)
