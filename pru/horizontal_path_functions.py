# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Horizontal path functions.
"""

import numpy as np
import scipy.stats
from .EcefPoint import EcefPoint, distance_radians, SQ_MIN_LENGTH
from .EcefArc import EcefArc
from .TurnArc import MIN_TURN_ANGLE, MAX_TURN_ANGLE
from .EcefPath import EcefPath
from .ecef_functions import calculate_xtds, calculate_atds, \
    find_furthest_distance, find_most_extreme_value

TWENTY_NM = np.deg2rad(1.0 / 3.0)
TWO_NM = np.deg2rad(1.0 / 30.0)

MINIMUM_ARC_LENGTH = np.deg2rad(0.1 / 60.0)
""" The minimum arc length in radians, 0.1 NM. """


def find_extreme_point_index(ecef_points, first_index, last_index,
                             threshold, xtd_ratio):
    """
    The index of the point furthest from the Arc between first_index and
    last_index.

    If the Arc is longer than MINIMUM_ARC_LENGTH, it finds the point with the
    largest across track distance. If the distance is larger than threshold
    or xtd_ratio time the arc length, it returns the index of the point.

    If the Arc is not longer than MINIMUM_ARC_LENGTH, if finds the furthest point
    the start. If the distance from the point to the start and end points is
    greater than MINIMUM_ARC_LENGTH, it returns the index of the point.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The trajectory points in ECEF coordinates.

    first_index, last_index: integers
        Indicies of the first and last points to use.

    threshold: float
        The across track distance threshold.

    Returns
    -------
    The index of the point furthest from the Arc joining the points at
    first_index and last_index.
    """
    max_xtd_index = last_index
    # If there is at least a point between first_index and last_index
    if ((last_index - first_index) > 1):
        arc = EcefArc(ecef_points[first_index], ecef_points[last_index])
        # first point is after arc start
        # xtd_index = first_index + 1
        if arc.length > MINIMUM_ARC_LENGTH:
            # calculate cross track distances relative to the base arc
            xtds = calculate_xtds(arc, ecef_points[first_index + 1: last_index])
            max_xtd, xtd_index = find_most_extreme_value(xtds)
            xtd_index += 1
            # set the threshold to the minimum of the threshold or a
            # fraction of the arc length
            xtd_threshold = min(threshold, xtd_ratio * arc.length)
            xtd_threshold = max(xtd_threshold, MINIMUM_ARC_LENGTH)
            if (np.abs(max_xtd) > xtd_threshold):
                # if the point is further than the threshold, return it
                max_xtd_index = first_index + xtd_index
        else:  # short arc
            # calculate the furthest point from the start point
            distance, xtd_index = \
                find_furthest_distance(ecef_points[first_index: last_index])
            if (distance > MINIMUM_ARC_LENGTH):
                # ensure that the point is far enough from the end point
                xtd_index += first_index
                end_distance = distance_radians(ecef_points[xtd_index],
                                                ecef_points[last_index])
                if end_distance > MINIMUM_ARC_LENGTH:
                    max_xtd_index = xtd_index

    return max_xtd_index


def find_extreme_point_indicies(ecef_points, threshold, *, xtd_ratio=0.1):
    """
    The indicies of the most extreme points including the first and last points.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The trajectory points in ECEF coordinates.

    threshold: float
        The across track distance threshold [radians]

    Returns
    -------
    The indicies of the first and last points and points inbetween which
    may be:
       turning points
       holding points
       erroneous data points

    joining the points at first_index and last_index.
    If the maximum across track distance is less than threshold,
    returns last_index.
    """
    finish_index = len(ecef_points) - 1
    start_index = 0
    indicies = np.zeros(1, dtype=int)

    if (2 < len(ecef_points)):
        # ensure that a point is further tha threshold from the start point
        distance, index = find_furthest_distance(ecef_points)
        if threshold < distance:
            # calculate the index of the most extreme point
            index = find_extreme_point_index(ecef_points, start_index,
                                             finish_index, threshold, xtd_ratio)
            last_index = finish_index
            last_indicies = []
            # loop until all extreme points found
            while index < finish_index:
                # if an extreme point was found
                if index < last_index:
                    # keep searching toward the start
                    last_indicies.append(last_index)
                    last_index = index
                else:
                    # last_index is next most extreme point from start
                    indicies = np.append(indicies, last_index)
                    # serach along next leg away from start
                    start_index = last_index
                    index = start_index
                    last_index = last_indicies.pop()

                # calculate the index of the next extreme point
                index = find_extreme_point_index(ecef_points, start_index,
                                                 last_index, threshold, xtd_ratio)

    indicies = np.append(indicies, finish_index)

    return indicies


def fit_arc_to_points(ecef_points, arc):
    """
    Calculates a closest arc through ecef_points.

    Note: there must be at least 2 ecef_points.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The points in ECEF coordinates.

    arc: EcefArc
        An initial arc to match the ecef_points.

    Returns
    -------
        A closest arc through ecef_points, minimising their across track distances.
    """
    atds = calculate_atds(arc, ecef_points)
    xtds = calculate_xtds(arc, ecef_points)
    # calculate the slope and intercept of the closest line through the  points
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(atds, xtds)
    a = arc.perp_position(arc.a, intercept)
    b = arc.perp_position(arc.b, intercept + arc.length * slope)
    return EcefArc(a, b)


def calculate_intersection(prev_arc, arc):
    """
    Calculates the intersection point between a pair of arcs.

    If the arcs are on (or very close to) the same Great Circle, it returns
    the start point of the second arc.

    Parameters
    ----------
    prev_arc, arc: EcefArcs
        The arcs before and after the intersection.

    Returns
    -------
        The intersection point of the arcs.
    """
    coords = np.cross(prev_arc.pole, arc.pole)
    norm = np.dot(coords, coords)
    if norm > SQ_MIN_LENGTH:
        coords /= np.sqrt(norm)
        # test for antipodal intersection point
        coords = -coords if (np.dot(coords, arc.a) < 0.0) else coords
    else:  # same Great Circle
        coords = arc.a

    return EcefPoint(coords)


def calculate_max_turn_initiation_distance(in_length, out_length, *,
                                           max_distance=TWENTY_NM):
    """
    Calculates the maximum initation distance of a turn from its inbound and
    outbound leg lengths.

    Note: the default maximum intiation distance is 20 NM, see ICAO 9905
    AN/471 Required Navigation Performance Authorization

    Parameters
    ----------
    in_length, out_length: float
        The length sof the arcs before and after the intersection [radians].

    max_distance : float
        The maximum permitted initation distance, default 20 NM [radians].

    Returns
    -------
        The maximum turn initation distance [radians].
    """
    return min(min(in_length, out_length) / 2, max_distance)


def derive_horizontal_path(ecef_points, threshold):
    """
    Derive horizontal path waypoints and turn anticipation distances from
    ECEF points.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The trajectory points in ECEF coordinates.

    threshold: float
        The across track distance threshold [radians]

    Returns
    -------
        The EcefPath between the ecef_points.
    """
    # Find extreme points and their indicies in the ecef_points array
    indicies = find_extreme_point_indicies(ecef_points, threshold)
    extreme_points = ecef_points[[indicies]]

    # Calculate the Great Circle arc along the first route leg
    prev_index = 0
    index = indicies[1]
    prev_arc = EcefArc(extreme_points[0], extreme_points[1])
    prev_arc = fit_arc_to_points(ecef_points[prev_index: index + 1], prev_arc)

    # Create lists for the waypoints and turn initiation distances
    # Starting with the first point
    path_waypoints = [EcefPoint(prev_arc.a)]
    turn_distances = [0.0]

    prev_length = prev_arc.length
    for i in range(1, len(extreme_points) - 1):
        # Calculate the Great Circle arc along the next route leg
        prev_index = index
        index = indicies[i + 1]
        arc = EcefArc(extreme_points[i], extreme_points[i + 1])
        arc = fit_arc_to_points(ecef_points[prev_index: index + 1], arc)

        # Calculate the turn parameters at the waypoint
        turn_angle = prev_arc.turn_angle(arc.b)
        turn_distance = calculate_max_turn_initiation_distance(prev_length, arc.length)

        # Determine whether the turn is valid, calculate waypoint and
        # turn initiation distance accordingly
        is_valid_turn = (MIN_TURN_ANGLE < abs(turn_angle) <= MAX_TURN_ANGLE) and \
            (turn_distance > TWO_NM)
        waypoint = calculate_intersection(prev_arc, arc) if is_valid_turn \
            else EcefPoint(arc.a)  # the start point of the next arc
        turn_distance = turn_distance if is_valid_turn else 0.0

        turn_distances.append(turn_distance)
        path_waypoints.append(waypoint)

        prev_arc = arc
        prev_length = arc.length

    # Add the last point
    path_waypoints.append(EcefPoint(prev_arc.b))
    turn_distances.append(0.0)

    return EcefPath(path_waypoints, turn_distances)
