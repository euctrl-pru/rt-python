# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to interpolate trajectory position data.
"""

import numpy as np
import pandas as pd
from via_sphere import calculate_latitudes, calculate_longitudes
from .SpherePath import PointType
from .trajectory_functions import calculate_date_times, calculate_speed, \
    calculate_vertical_speed, convert_angle_to_track_angle
from .trajectory_fields import POSITION_FIELDS

DEFAULT_STRAIGHT_INTERVAL = 5.0
""" The default straight section interval, 5 seconds. """

DEFAULT_TURN_INTERVAL = 5.0
""" The default turn section interval, 5 seconds. """

POSITION_FIELD_LIST = POSITION_FIELDS.split(',')[:-4]
""" The output position fields. """


def calculate_interpolation_times(point_times, point_types,
                                  straight_interval, turn_interval):
    """
    Interpolate point_times at the given straight and turn intervals.

    Parameters
    ----------
    point_times: float array
        An ordered array of elapsed times in [Seconds].

    point_types: PointType array
        An array of PointType corresponding to the point_times.

    straight_interval: float
        The time interval between points on straight legs.

    turn_interval: float
        The time interval between points around turns.

    Returns
    -------
    times : float array
        The elapsed times at the requried intervals in [Seconds].

    """
    prev_time = point_times[0]
    times = [prev_time]
    is_turning = (point_types[0] == PointType.TurnStart)
    for i in range(1, len(point_times)):
        next_time = point_times[i]
        delta_time = next_time - prev_time
        interval = turn_interval if is_turning else straight_interval
        if delta_time > interval:
            for j in range(int(delta_time) // int(interval)):
                prev_time += interval
                times.append(prev_time)

        times.append(next_time)
        is_turning = (point_types[i] == PointType.TurnStart)
        prev_time = next_time

    return np.array(times)


def calculate_speeds(times, distances):
    """
    Calculate speeds from the given times and distances.

    Parameters
    ----------
    times: float array
        An increaing array of elapsed times in [Seconds].

    distances: float array
        A monotonic array of distances at the point_times in [Nautical Miles].

    Returns
    -------
    speeds : float array
        The speeds in [Knots].

    """
    delta_times = np.ediff1d(times)
    delta_distances = np.ediff1d(distances)
    speeds = calculate_speed(delta_distances, delta_times)

    last_value = speeds[-1]
    return np.append(speeds, last_value)


def calculate_vertical_speeds(times, altitudes):
    """
    Calculate vertical speeds from the given times and altitudes.

    Parameters
    ----------
    times: float array
        An increasing array of elapsed times in [Seconds].

    altitudes: float array
        A array of altitudes at the point_times in [feet].

    Returns
    -------
    vertical_speeds : float array
        The vertical_speeds in [feet per minute].

    """
    delta_times = np.ediff1d(times)
    delta_altitudes = np.ediff1d(altitudes)
    vertical_speeds = calculate_vertical_speed(delta_altitudes, delta_times)

    last_value = vertical_speeds[-1]
    return np.append(vertical_speeds, last_value)


def interpolate_trajectory_positions(smooth_traj, straight_interval, turn_interval):
    """
    Interpolate trajectory positions from a smoothed trajectory.

    The function:
        - converts the SmoothedTrajectory HorizontalPath into an SpherePath
        - get the turn point distances and point types from ecef_path
        - calls calculate_interpolation_times to get the output times
        - calls time_profile.interpolate_by_elapsed_time to get the distances
        - calls AltitudeProfile.interpolate, ecef_path.calculate_positions, etc
        to calculate interpolated altitudes, positions, speeds, etc. at the distances.

    Parameterscd ../ap
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    straight_interval: float
        A DataFrame containing raw positions for a flight, sorted in time order.

    turn_interval: float
        The maximum across track distance[Nautical Miles], default: 0.25 NM.

    Returns
    -------
    positions: a pandas DataFrame
        The interpolated trajectory positions.

    """
    # Construct the SpherePath corresponding to the HorizontalPath
    ecef_path = smooth_traj.path.ecef_path()

    # Get the turn point distances from ecef_path
    point_distances, point_types = ecef_path.section_distances_and_types()
    point_times = smooth_traj.timep.interpolate_by_distance(point_distances)
    # insert times based on straight_interval and turn_interval
    times = calculate_interpolation_times(point_times, point_types,
                                          straight_interval, turn_interval)
    distances = smooth_traj.timep.interpolate_by_elapsed_time(times)
    altitudes = smooth_traj.altp.interpolate(distances)

    # calculate points at path disatnces
    points = ecef_path.calculate_positions(distances)
    lats = calculate_latitudes(points)
    lons = calculate_longitudes(points)

    # calculate speeds, etc from times, distances and altitudes
    speeds = calculate_speeds(times, distances)
    ground_tracks = convert_angle_to_track_angle(ecef_path.calculate_ground_tracks(distances))
    vert_speeds = calculate_vertical_speeds(times, altitudes)

    # convert elapsed times to date_times
    date_times = calculate_date_times(times, smooth_traj.timep.start_time)

    # Create an array of flight_ids
    flight_id = np.array(len(date_times), dtype='object')
    flight_id.fill(str(smooth_traj.flight_id))

    # return the data in a pandas DataFrame with trajectory_fields.POSITION_FIELDS
    return pd.DataFrame({'FLIGHT_ID': flight_id,
                         'DISTANCE': distances,
                         'TIME': date_times,
                         'LAT': lats,
                         'LON': lons,
                         'ALT': altitudes,
                         'SPEED_GND': speeds,
                         'TRACK_GND': ground_tracks,
                         'VERT_SPEED': vert_speeds},
                        columns=POSITION_FIELD_LIST)
