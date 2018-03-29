# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to interpolate trajectory position data.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from .EcefPath import PointType, EcefPath
from .ecef_functions import calculate_EcefPoints, calculate_LatLongs
from pru.trajectory_fields import POSITION_FIELDS

DEFAULT_STRAIGHT_INTERVAL = 6.0
""" The default straight section interval, 6 seconds. """

DEFAULT_TURN_INTERVAL = 1.0
""" The default turn section interval, 1 second. """

POSITION_FIELD_LIST = POSITION_FIELDS.split(',')[:-4]
""" The output position fields. """


def interpolate_altitude_profile(altp, distances):
    """
    Interpolate altitudes at distance values.

    Uses the scipy.interpolate.CubicSpline function to interpolate
    altitudes at the required distances.

    Parameters
    ----------
    altp: an AltitudeProfile
        An AltitudeProfile object.

    distances: float array
        An ordered array of distances in [Nautical Miles].

    Returns
    -------
    alts : float array
        The interpolated altitudes at the given distances.
    """
    cs = CubicSpline(altp.distances, altp.altitudes)
    return cs(distances)


def interpolate_time_profile_by_distance(timep, distances):
    """
    Interpolate elapsed_times at the distance values.

    Uses the scipy.interpolate.CubicSpline function to interpolate
    times at the required distances.

    Parameters
    ----------
    timep: a TimeProfile
        A TimeProfile object.

    distances: float array
        An ordered array of distances in [Nautical Miles].

    Returns
    -------
    times : float array
        The elapsed_times at the given distance values in [Seconds].
    """
    cs = CubicSpline(timep.distances, timep.elapsed_times)
    return cs(distances)


def interpolate_time_profile_by_elapsed_time(timep, times):
    """
    Interpolate distances at the elapsed time values.

    Uses the scipy.interpolate.CubicSpline function to interpolate
    distances at the required elapsed times.

    Parameters
    ----------
    timep: a TimeProfile
        A TimeProfile object.

    times: float array
        An ordered array of elapsed_times in [Seconds].

    Returns
    -------

    distances : float array
        The distances at the given time values in [Nautical Miles].
    """
    cs = CubicSpline(timep.elapsed_times, timep.distances)
    return cs(times)


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
    speeds = 3600.0 * delta_distances / delta_times

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
    vertical_speeds = 60.0 * delta_altitudes / delta_times

    last_value = vertical_speeds[-1]
    return np.append(vertical_speeds, last_value)


def convert_ground_tracks(angles):
    """
    Convert ground track angles from radians to degrees.

    Parameters
    ----------
    angles: float array
        An array of angles in [radians].

    Returns
    -------
    tracks : float array
        The ground tracks in [degrees], where 0.0 <= track < 360.0.
    """
    tracks = np.zeros(len(angles))
    for i, angle in enumerate(angles):
        tracks[i] = np.rad2deg(angle + 2.0 * np.pi if angle < 0.0 else angle)
    return tracks


def interpolate_trajectory_positions(smooth_traj, straight_interval, turn_interval):
    """
    Interpolate trajectory positions from a smoothed trajectory

    The function:
        - converts the SmoothedTrajectory HorizontalPath into an EcefPath
        - get the turn point distances and point types from ecef_path
        - calls calculate_interpolation_times to get the output times
        - calls interpolate_time_profile_by_elapsed_time to get the distances
        - calls interpolate_altitude_profile, ecef_path.calculate_positions, etc
        to calculate interpolated altitudes, positions, speeds, etc. at the distances.

    Parameters
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
    # Convert the HorizontalPath into an EcefPath
    ecef_points = calculate_EcefPoints(smooth_traj.path.lats, smooth_traj.path.lons)
    tids = np.deg2rad(smooth_traj.path.tids / 60.0)
    ecef_path = EcefPath(ecef_points, tids)

    # Get the turn point distances from ecef_path
    point_distances, point_types = ecef_path.section_distances_and_types()
    point_times = interpolate_time_profile_by_distance(smooth_traj.timep,
                                                       point_distances)
    # insert times based on straight_interval and turn_interval
    times = calculate_interpolation_times(point_times, point_types,
                                          straight_interval, turn_interval)
    distances = interpolate_time_profile_by_elapsed_time(smooth_traj.timep, times)
    altitudes = interpolate_altitude_profile(smooth_traj.altp, distances)

    # calculate points at path disatnces
    points = ecef_path.calculate_positions(distances)
    lats, lons = calculate_LatLongs(points)

    # calculate speeds, etc from times, distances and altitudes
    speeds = calculate_speeds(times, distances)
    ground_tracks = convert_ground_tracks(ecef_path.calculate_ground_tracks(distances))
    vert_speeds = calculate_vertical_speeds(times, altitudes)

    # convert times to date_times
    date_times = smooth_traj.timep.start_time + times * np.timedelta64(1, 's')

    # Create an array of flight_ids
    flight_id = np.array(len(date_times), dtype=np.string_)
    flight_id.fill(str(smooth_traj.flight_id))

    # return the data in a pandas DataFrame with trajectory_fields.POSITION_FIELDS
    return pd.DataFrame({'FLIGHT_ID': flight_id,
                         'DISTANCE': distances,
                         'TIME_CALCULATED': date_times,
                         'LAT': lats,
                         'LON': lons,
                         'ALT': altitudes,
                         'SPEED_GND': speeds,
                         'TRACK_GND': ground_tracks,
                         'VERT_SPEED': vert_speeds},
                        columns=POSITION_FIELD_LIST)
