# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Common trajectory matching functions.
"""

import bisect
from via_sphere import distance_radians
from .sphere_functions import calculate_position
from .trajectory_functions import calculate_common_period, calculate_delta_time, \
    calculate_value_reference, calculate_value, calculate_speed, rad2nm


def distance_nm(a, b):
    """
    Calculate the Great Circle distance between two EcefPoints: a and b.

    Parameters
    ----------
    a, b: EcefPoints.

    Returns
    -------
    distance: float
        The Great Circle distance between a and b in [Nautical Miles].

    """
    return rad2nm(distance_radians(a, b))


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
