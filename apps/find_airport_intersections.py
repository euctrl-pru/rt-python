#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Find trajectory airport intersections.
"""

import sys
import os
import errno
import pandas as pd
from via_sphere import global_Point3d
from pru.SmoothedTrajectory import generate_SmoothedTrajectories
from pru.trajectory_airport_intersections import find_airport_intersection, \
    DEFAULT_RADIUS, DEFAULT_DISTANCE_TOLERANCE
from pru.trajectory_fields import ISO8601_DATETIME_US_FORMAT,  BZ2_FILE_EXTENSION, \
    CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, has_bz2_extension, \
    read_iso8601_date_string, is_valid_iso8601_date, AIRPORT_INTERSECTION_FIELDS
from pru.trajectory_files import TRAJECTORIES, AIRPORT_INTERSECTIONS
from pru.logger import logger


log = logger(__name__)

DEFAULT_MOVEMENTS_AIRPORTS_FILENAME = 'movements_reporting_airports.csv'
""" The default name of the file containing the airports. """

AIRPORT_NAME_LENGTH = 4
""" The length of an airport name. """

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def find_airport_intersections(flights_filename, trajectories_filename,
                               radius=DEFAULT_RADIUS,
                               airports_filename=DEFAULT_MOVEMENTS_AIRPORTS_FILENAME,
                               distance_tolerance=DEFAULT_DISTANCE_TOLERANCE):
    """
    Find intersections between trajectories and airport cylinders.

    Parameters
    ----------
    flights_filename: a string
        The name of a flights file.

    trajectories_filename: a string
        The name of a trajectories file.

    radius: float
        The radius of the cylinder aroud each airport [Nautical Miles],
        default DEFAULT_RADIUS.

    airports_filename: a string
        The name of the airports file, default DEFAULT_MOVEMENTS_AIRPORTS_FILENAME.

    distance_tolerance: float
        The tolerance for path and cylinder distances,
        default DEFAULT_DISTANCE_TOLERANCE.

    Returns
    -------
    An errno error_code if an error occured, zero otherwise.

    """
    # Extract the date string from the filename and validate it
    flights_date = read_iso8601_date_string(flights_filename)
    if is_valid_iso8601_date(flights_date):
        log.info(f'flights file: {flights_filename}')
    else:
        log.error(f'flights file: {flights_filename}, invalid date: {flights_date}')
        return errno.EINVAL

    trajectories_date = read_iso8601_date_string(trajectories_filename,
                                                 is_json=True)
    if is_valid_iso8601_date(trajectories_date):
        log.info(f'trajectories file: {trajectories_filename}')
    else:
        log.error(f'trajectories file, invalid date: {trajectories_date}')
        return errno.EINVAL

    if flights_date != trajectories_date:
        log.error(f'Files are not for the same date! Flights date: {flights_date}'
                  f', trajectories date: {trajectories_date}')
        return errno.EINVAL

    log.info(f'flights file: {flights_filename}')
    log.info(f'trajectories file: {trajectories_filename}')
    log.info(f'radius: {radius} NM')
    log.info(f'distance_tolerance: {distance_tolerance} NM')

    airports_df = pd.DataFrame()
    try:
        airports_df = pd.read_csv(airports_filename,
                                  index_col='AIRPORT',
                                  memory_map=True)

        log.info(f'{airports_filename} read ok')
    except EnvironmentError:
        log.error(f'could not read file: {airports_filename}')
        return errno.ENOENT

    flights_df = pd.DataFrame()
    try:
        flights_df = pd.read_csv(flights_filename,
                                 usecols=['FLIGHT_ID', 'ADEP', 'ADES'],
                                 index_col='FLIGHT_ID',
                                 memory_map=True)

        log.info(f'{flights_filename} read ok')
    except EnvironmentError:
        log.error(f'could not read file: {flights_filename}')
        return errno.ENOENT

    # Determine the departure and arrival flights
    departures_df = pd.merge(flights_df, airports_df,
                             left_on='ADEP', right_index=True)
    destinations_df = pd.merge(flights_df, airports_df,
                               left_on='ADES', right_index=True)

    trajectories_filename = os.path.basename(trajectories_filename)
    is_bz2 = has_bz2_extension(trajectories_filename)
    if is_bz2:  # remove the .bz2 from the end of the filename
        trajectories_filename = trajectories_filename[:-len(BZ2_FILE_EXTENSION)]

    # Write the airport_intersections into a csv file with output_filename
    output_filename = trajectories_filename.replace(TRAJECTORIES, AIRPORT_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)
    try:
        with open(output_filename, 'w') as file:
            file.write(AIRPORT_INTERSECTION_FIELDS)

            flights_count = 0
            smoothed_trajectories = generate_SmoothedTrajectories(trajectories_filename)
            for smooth_traj in smoothed_trajectories:
                try:
                    flight_id = smooth_traj.flight_id

                    is_departure = flight_id in departures_df.index
                    is_arrival = flight_id in destinations_df.index

                    if is_departure or is_arrival:

                        traj_path = smooth_traj.path.ecef_path()

                        if is_departure:
                            dep_row = departures_df.loc[flight_id]
                            departure = dep_row['ADEP']
                            if len(departure) == AIRPORT_NAME_LENGTH:
                                latitude = dep_row['LATITUDE']
                                longitude = dep_row['LONGITUDE']
                                ref_point = global_Point3d(latitude, longitude)
                                dep_intersection = find_airport_intersection(smooth_traj, traj_path,
                                                                             departure, ref_point,
                                                                             radius, False,
                                                                             distance_tolerance)
                                if not dep_intersection.empty:
                                    dep_intersection.to_csv(file, index=False,
                                                            header=False, mode='a',
                                                            date_format=ISO8601_DATETIME_US_FORMAT)

                        if is_arrival:
                            dest_row = destinations_df.loc[flight_id]
                            destination = dest_row['ADES']
                            if len(destination) == AIRPORT_NAME_LENGTH:
                                latitude = dest_row['LATITUDE']
                                longitude = dest_row['LONGITUDE']
                                ref_point = global_Point3d(latitude, longitude)
                                dest_intersection = find_airport_intersection(smooth_traj, traj_path,
                                                                              destination, ref_point,
                                                                              radius, True,
                                                                              distance_tolerance)
                                if not dest_intersection.empty:
                                    dest_intersection.to_csv(file, index=False,
                                                             header=False, mode='a',
                                                             date_format=ISO8601_DATETIME_US_FORMAT)

                    flights_count += 1

                except ValueError:
                    log.exception(f'find_airport_intersections id: {flight_id}')

                except StopIteration:
                    pass

            log.info(f'find_airport_intersections finished for {flights_count} trajectories.')

    except EnvironmentError:
        log.error(f'could not write file: {output_filename}')
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: find_airport_intersections.py <flights_filename>'
              ' <trajectories_filename> [radius] [airports_filename]'
              ' [distance_tolerance]')
        sys.exit(errno.EINVAL)

    radius = DEFAULT_RADIUS
    if len(sys.argv) >= 4:
        try:
            radius = float(sys.argv[3])
        except ValueError:
            log.error('invalid radius: %s', sys.argv[3])
            sys.exit(errno.EINVAL)

    airports_filename = DEFAULT_MOVEMENTS_AIRPORTS_FILENAME
    if len(sys.argv) >= 5:
        airports_filename = sys.argv[4]

    distance_tolerance = DEFAULT_DISTANCE_TOLERANCE
    if len(sys.argv) >= 6:
        try:
            distance_tolerance = float(sys.argv[5])
        except ValueError:
            log.error('invalid distance_tolerance: %s', sys.argv[5])
            sys.exit(errno.EINVAL)

    error_code = find_airport_intersections(sys.argv[1], sys.argv[2],
                                            radius, airports_filename,
                                            distance_tolerance)
    if error_code:
        sys.exit(error_code)
