# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module contains functions to support trajectory algorithms.
"""
import numpy as np
import bisect
from .EcefPoint import distance_nm
from .ecef_functions import *


def calculate_delta_time(time0, time1):
    """ Calculate the time difference in seconds between a pair of datetime64s. """
    return (time1 - time0) / np.timedelta64(1, 's')


def calculate_elapsed_times(datetimes, ref_datetime):
    """
    Calculate the elapsed times between datetimes and ref_datetime.

    Parameters
    ----------
    datetimes: a numpy array of numpy datetime64s
        An array of datetimes.
        Note: numpy datetime64s are not compatible with python datetimes.

    ref_datetime: a numpy datetime64s
        The reference date time.

    Returns
    -------
    elapsed_times: a numpy array of float durations from ref_datetime in [Seconds]
    """
    return calculate_delta_time(ref_datetime, datetimes)


def calculate_date_times(times, ref_datetime):
    """
    Calculate the datetimes from elapsed times and ref_datetime.

    Parameters
    ----------
    times: a numpy array of float durations from ref_datetime in [Seconds]
        An array of datetimes.

    ref_datetime: a numpy datetime64s
        The reference date time.

        Note: numpy datetime64s are not compatible with python datetimes.
    Returns
    -------
    datetimes: a numpy array of numpy datetime64s in microsecond precision.
    """
    return ref_datetime + 1000000.0 * times * np.timedelta64(1, 'us')


def calculate_leg_durations(datetimes):
    """
    Calculate leg durations (in seconds) between adjacent datetimes.

    Parameters
    ----------
    datetimes: a numpy array of numpy datetime64s
        An array of datetimes.
        Note: numpy datetime64s are not compatible with python datetimes.

    Returns
    -------
    durations: a numpy array of float durations between datetimes in [Seconds]
    Note: the first value is always zero.
    """
    times = calculate_elapsed_times(datetimes, datetimes[0])
    return np.ediff1d(times, to_begin=[0])


def calculate_speed(distance, time, *, min_time=0.5):
    """
    Calculate the speed in Knots given the distance and time.

    Parameters
    ----------
    distance: float
        The distance [Nautical Miles].

    time: float
        The time [Seconds].

    min_time: float
        The minimum time, default 0.5 [Seconds].

    Note: if time is not greater than zero, min_time is used instead.

    Returns
    -------
    The speed [Knots]

    """
    return 3600.0 * distance / np.where(time > 0.0, time, min_time)


def calculate_min_speed(distance, time, distance_accuracy, time_precision):
    """
    Calculate the speed in Knots given the distance and time between
    positions taking the distance_accuracy and time_precision into account.
    I.e. the slowest possible speed between the positions.

    Parameters
    ----------
    distance: float
        The distance positions [Nautical Miles].

    time: float
        The time between positions [Seconds].

    distance_accuracy: float
        The maximum distance between positions at the same time [Nautical Miles].

    time_precision: float
        The precision of time measurement [Seconds].

    Returns
    -------
    The speed [Knots] taking the distance_accuracy and time_precision into
    account.
    """
    return calculate_speed(distance - distance_accuracy, time + time_precision)


def find_duplicate_values(values, min_value):
    """
    Find positions of values < min_value from the previous value.

    Parameters
    ----------
    values: a numpy array of floats
        The values.

    min_value: float
        The minimum difference between positions.
        Note: pre condition min_value < 100

    Returns
    -------
        A numpy boolean array with duplicate values set to True.

    """
    return np.ediff1d(values, to_begin=100) < min_value


def max_delta(deltas):
    """ Return the most extreme value (positive or negative). """
    return max(deltas.max(), abs(deltas.min()))


def calculate_altitude_differences(alts):
    """
    Calculate differences (in feet) between adjacent altitudes.

    Parameters
    ----------
    alts: a numpy array of floats
        An array of altitudes.

    Returns
    -------
    delta_alts: a numpy array of float differences between altitudes [feet]
    Note: the first value is always zero.
    """
    return np.ediff1d(alts, to_begin=[0])


def calculate_vertical_speed(altitude, time, *, min_time=0.5):
    """
    Calculate the vertical speed in feet per minute given the altitude and time.

    Parameters
    ----------
    altitude: float
        The altitude [feet].

    time: float
        The time [Seconds].

    min_time: float
        The minimum time, default 0.5 [Seconds].

    Note: if time is not greater than zero, min_time is used instead.

    Returns
    -------
    The vertical speed [feet per minute]

    """
    return 60.0 * altitude / np.where(time > 0.0, time, min_time)


def convert_angle_to_track_angle(angle):
    """
    Convert angles in radians to angles in degrees from 0 to 360.

    Note: uses the numpy ufunc: where so that it also operates on numpy arrays.

    Parameters
    ----------
    angle: float
        An angle in [radians].

    Returns
    -------
    The angle in [degrees], where 0.0 <= angle < 360.0.
    """
    return np.rad2deg(np.where(angle < 0.0, angle + 2.0 * np.pi, angle))


def calculate_common_period(a_times, b_times):
    """
    Calculate the common period between two time series.

    Parameters
    ----------
    a_times, b_times: numpy arrays of numpy datetime64s
        Arrays of datetimes.

    Returns
    -------
    start_time: the latest of the two series start times.
    finish_time: the earliest of the two series finish times.
    """
    start_time = max(a_times[0], b_times[0])
    finish_time = min(a_times[-1], b_times[-1])

    return start_time, finish_time


def calculate_value_reference(values, value, *, is_time=False):
    """
    Find the index and ratio of value in values.

    Parameters
    ----------
    values: numpy arrays of values
        Array of values.

    value:
        The value to search for.

    is_time: Boolean
        True if the values are numpy datetime64s, False otherwise.

    Returns
    -------
    index: the index of the value or just before the value
    ratio: the ratio from index to the value. Zero if the value is at index.
    0.0 <= ratio < 1.0
    """
    index = bisect.bisect_left(values, value)
    ratio = 0.0
    index_value = values[index]
    if (index > 0) and (value < index_value):
        index -= 1
        denom = calculate_delta_time(values[index], index_value) if is_time else \
            index_value - values[index]

        if (denom > 0.0):
            delta = calculate_delta_time(values[index], value) if is_time else \
                value - values[index]
            ratio = delta / denom

    return index, ratio


def calculate_value(values, index, ratio=0.0):
    """
    The value of something at index and ratio along a list of values.

    Parameters
    ----------
    values: values array
        An array of values.

    index: integer
        The index of the value, or the value before if ratio > 0.0

    ratio: ratio
        The ratio of the value after index, default 0.0.
        0.0 <= ratio < 1.0

    Returns
    -------
    The value at index and ratio along the values array.
    """
    value = values[-1]
    if index < len(values):
        value = values[index]
        if ratio > 0.0:
            if index < len(values) - 1:
                delta = values[index + 1] - value
                value += ratio * delta

    return value


def compare_trajectory_positions(a_times, b_times, a_points, b_points,
                                 a_alts, b_alts, *, distance_threshold=2.0,
                                 alt_threshold=200.0, time_threshold=0.0,
                                 speed_threshold=750.0):
    """
    Compare trajectory points to determine whether they are for the same flight.

    Parameters
    ----------
    a_times, b_times: numpy arrays of numpy datetime64s
        Arrays of datetimes representing trajectory times.
        Note: numpy datetime64s are not compatible with python datetimes.

    a_points, b_points: numpy arrays of EcefPoints
        Arrays of EcefPoints representing trajectory horizontal positions.

    a_alts, b_alts: numpy arrays of floats
        Arrays of floats representing trajectory altitudes.

    distance_threshold: float
        The distance threshold [Nautical Miles] above which positions are
        not considered to be on the same trajectory, default 2 NM.

    alt_threshold: float
        The altitude threshold [feeet] above which positions are
        not considered to be on the same trajectory, default 200 feet.

    time_threshold: float
        The maximum time [seconds] between trajectory positions to be
        considered to be on the same trajectory, default zero seconds.

    speed_threshold: float
        The maximum speed [Knots] between trajectory positions to be
        considered to be on the same trajectory, default 600 Knots.

    Returns
    -------
    returns True if the trajectories are for the same flight, False otherwise.
    """
    distance = 0.0
    start_time, finish_time = calculate_common_period(a_times, b_times)
    delta_time = calculate_delta_time(finish_time, start_time)
    if delta_time < 0.0:   # times overlap
        # Calculate distance between points at the start
        a_index, a_ratio = calculate_value_reference(a_times, start_time, is_time=True)
        b_index, b_ratio = calculate_value_reference(b_times, start_time, is_time=True)
        point_a = calculate_position(a_points, a_index, a_ratio)
        point_b = calculate_position(b_points, b_index, b_ratio)
        distance = distance_nm(point_a, point_b)

        if distance > distance_threshold:
            return False

        # Calculate altitude between points at the start
        alt_a = calculate_value(a_alts, a_index, a_ratio)
        alt_b = calculate_value(b_alts, b_index, b_ratio)
        delta_alt = abs(alt_a - alt_b)

        if delta_alt > alt_threshold:
            return False

        # Calculate distance between points at the finish
        a_index, a_ratio = calculate_value_reference(a_times, finish_time, is_time=True)
        b_index, b_ratio = calculate_value_reference(b_times, finish_time, is_time=True)
        point_a = calculate_position(a_points, a_index, a_ratio)
        point_b = calculate_position(b_points, b_index, b_ratio)
        distance = distance_nm(point_a, point_b)

        # Calculate altitude between points at the finish
        alt_a = calculate_value(a_alts, a_index, a_ratio)
        alt_b = calculate_value(b_alts, b_index, b_ratio)
        delta_alt = abs(alt_a - alt_b)

    elif finish_time == start_time:  # trajectories have a single common time
        a_index = bisect.bisect_left(a_times, start_time)
        b_index = bisect.bisect_left(b_times, start_time)
        distance = distance_nm(a_points[a_index], b_points[b_index])
        delta_alt = abs(a_alts[a_index] - b_alts[b_index])

    else:  # trajectories do not overlap in time
        # determine whether they are within time_threshold
        if delta_time <= time_threshold:
            # determine whether they are within speed_threshold
            point_a = a_points[0]
            point_b = b_points[-1]
            distance = distance_nm(point_a, point_b)
            speed = calculate_speed(distance, delta_time)
            return speed <= speed_threshold
        else:
            return False

    return (distance <= distance_threshold) and (delta_alt <= alt_threshold)
