# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module contains functions to support trajectory algorithms.
"""
import numpy as np
import bisect
from .EcefPoint import distance_nm
from .ecef_functions import *


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
    durations = np.zeros(len(datetimes), dtype=float)
    prev_time = datetimes[0]
    for i, time in enumerate(datetimes):
        durations[i] = (time - prev_time) / np.timedelta64(1, 's')
        prev_time = time

    return durations


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
    delta_alts = np.zeros(len(alts), dtype=float)
    prev_alt = alts[0]
    for i, alt in enumerate(alts):
        delta_alts[i] = alt - prev_alt
        prev_alt = alt

    return delta_alts


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
        denom = index_value - values[index]
        denom = denom / np.timedelta64(1, 's') if is_time else denom
        if (denom > 0.0):
            delta = value - values[index]
            delta = delta / np.timedelta64(1, 's') if is_time else delta
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
                                 alt_threshold=200.0, time_threshold=0.0):
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

    Returns
    -------
    returns True if the trajectories are for the same flight, False otherwise.
    """
    distance = 0.0
    start_time, finish_time = calculate_common_period(a_times, b_times)
    delta_time = (start_time - finish_time) / np.timedelta64(1, 's')
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
        return delta_time <= time_threshold

    return (distance <= distance_threshold) and (delta_alt <= alt_threshold)
