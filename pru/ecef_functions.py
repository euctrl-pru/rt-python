# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports Earth Centred Earth Fixed (ECEF) coordinates.
"""
import numpy as np
from .EcefPoint import EcefPoint, distance_radians
from .EcefArc import EcefArc


def calculate_EcefPoints(lats, longs):
    """
    Construct a numpy array of EcefPoints from 2 arrays containing
    Latitudes and Longitudes.
    Note: lats and longs must be of equal lengths.

    Parameters
    ----------
    lats: float array
        An array of Latitudes in [degrees].

    longs: float array
        An array of Longitudes in [degrees].

    Returns
    -------
    ecef_points: a numpy array of EcefPoints
    """
    points = np.ndarray(len(lats), dtype=np.object)
    for i, lat_long in enumerate(zip(lats, longs)):
        points[i] = EcefPoint.from_lat_long(lat_long)

    return points


def calculate_leg_lengths(ecef_points):
    """
    Calculates distances (leg lengths) between adjacent ecef_points.

    Parameters
    ----------
    ecef_points: EcefPoints array
        An array of EcefPoints.

    Returns
    -------
    lengths: a numpy array of lengths between EcefPoints in [radians]
    Note: the first value is always zero.
    """
    lengths = np.zeros(len(ecef_points), dtype=float)
    prev_point = ecef_points[0]
    for i, point in enumerate(ecef_points):
        lengths[i] = distance_radians(prev_point, point)
        prev_point = point

    return lengths


def calculate_distances(ecef_points, ref_point):
    """
    Calculates distances (leg lengths) between ecef_points and ref_point.

    Parameters
    ----------
    ecef_points: EcefPoints array
        An array of EcefPoints.

    ref_point: EcefPoints
        The reference point to measure distance from.

    Returns
    -------
    distances: a numpy array of distances between ref_point and ecef_points
    in [radians]
    """
    distances = np.zeros(len(ecef_points), dtype=float)
    for i, point in enumerate(ecef_points):
        distances[i] = distance_radians(ref_point, point)
    return distances


def find_furthest_distance(ecef_points):
    """
    Returns the distance (and index) of the furthest point from the start.

    Parameters
    ----------
    ecef_points: EcefPoints array
        An array of EcefPoints.

    Returns
    -------
    The distance and index of the furthest point from the first point.
    """
    distances = calculate_distances(ecef_points, ecef_points[0])
    return distances.max(), distances.argmax()


def calculate_position(ecef_points, index, ratio=0.0):
    """
    The position of a point at index and ratio along a list of EcefPoints.

    Parameters
    ----------
    ecef_points: EcefPoints array
        An array of EcefPoints.

    index: integer
        The index of the point, or the point before if ratio > 0.0

    ratio: ratio
        The ratio of the position after the point at index, default 0.0.
        0.0 <= ratio < 1.0

    Returns
    -------
    The EcefPoint at index and ratio along the EcefPoints array.
    """
    point = ecef_points[index]
    if ratio > 0.0:
        if index < len(ecef_points) - 1:
            arc = EcefArc(point, ecef_points[index + 1])
            point = arc.position(ratio * arc.length)
        else:
            point = ecef_points[-1]

    return point


def calculate_xtds(arc, ecef_points):
    """
    Calculate across track distances of the ecef_points from the arc.

    Parameters
    ----------
    arc: EcefArc
        The EcefArc to measure across track distance from.

    ecef_points: EcefPoints array
        An array of EcefPoints.

    Returns
    -------
    The across track distances of the ecef_points from the arc in [radians].
    """
    xtds = np.zeros(len(ecef_points), dtype=float)

    for i, point in enumerate(ecef_points):
        xtds[i] = arc.cross_track_distance(point)

    return xtds


def calculate_atds(arc, ecef_points):
    """
    Calculate along track distances of the ecef_points along the arc.

    Parameters
    ----------
    arc: EcefArc
        The EcefArc to measure along track distance from.

    ecef_points: EcefPoints array
        An array of EcefPoints.

    Returns
    -------
    The along track distances of the ecef_points along the arc in [radians].
    """
    atds = np.zeros(len(ecef_points), dtype=float)

    for i, point in enumerate(ecef_points):
        atds[i] = arc.along_track_distance(point)

    return atds


def find_most_extreme_value(values):
    """
    Find the most extreme (signed) value and index of the value.

    Parameters
    ----------
    values: float array
        An array of signed values.

    Returns
    -------
    The value and index of the most extreme value.
    """
    max_value = values.max()
    min_value = values.min()
    max_value_index = values.argmin() if (max_value < -min_value) \
        else values.argmax()
    max_value = min_value if (max_value < -min_value) else max_value

    return max_value, max_value_index


def calculate_EcefArcs(ecef_points):
    """
    Construct a numpy array of EcefArcs from and array of EcefPoints.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The trajectory points in ECEF coordinates.

    Returns
    -------
    arcs: a numpy array of EcefArcs between the EcefPoints
    """
    arcs = np.ndarray(len(ecef_points), dtype=np.object)
    prev_point = ecef_points[0]
    for i, point in enumerate(ecef_points):
        arcs[i] = EcefArc(prev_point, point)
        prev_point = point

    return np.delete(arcs, 0)


def calculate_closest_distances(ecef_arcs, point):
    """
    Calculate the closest distances of the ecef_arcs to the point.

    Parameters
    ----------
    ecef_arcs: EcefArcs array
        The EcefArcs to measure distance from.

    point: EcefPoint
        The point to measure.

    Returns
    -------
    The closest distances of the ecef_arcs to the point in [radians].
    """
    distances = np.zeros(len(ecef_arcs), dtype=float)
    for i, arc in enumerate(ecef_arcs):
        distances[i] = arc.closest_distance(point)

    return distances


def find_index_and_ratio(ecef_points, point):
    """
    The index and ratio of the closest point along ecef_points to point.

    Parameters
    ----------
    ecef_points: numpy array of EcefPoints
        The trajectory points in ECEF coordinates.

    point: EcefPoint
        The point to find the closest point to.

    Returns
    -------
    The index and ratio of the closest point along the EcefPoints array.
    """
    # Calculate the closest distances of the point to the legs between points
    ecef_arcs = calculate_EcefArcs(ecef_points)
    distances = calculate_closest_distances(ecef_arcs, point)

    # The index of the closest leg
    index = distances.argmin()

    # Calculate the ratio along the closest leg
    arc = ecef_arcs[index]
    atd = arc.along_track_distance(point)
    ratio = atd / arc.length

    # if the closest point is at the end of the leg, use start of next leg
    if ratio >= 1.0:
        ratio = 0.0
        index += 1

    return index, ratio


def calculate_turn_angles(ecef_arcs):
    """
    Calculate the turn_angles between an array of EcefArcs.

    Parameters
    ----------
    ecef_arcs: EcefArcs array
        An array of EcefArcs where each arc starts where the previous arc finishes.

    Returns
    -------
    angles: a numpy array of turn angles between EcefArcs in [radians]
    Note: the first value and last values are always zero.
    """

    angles = np.zeros(len(ecef_arcs) + 1, dtype=float)
    prev_arc = ecef_arcs[0]
    for i, arc in enumerate(ecef_arcs):
        angles[i] = prev_arc.turn_angle(arc.b)
        prev_arc = arc

    return angles
