# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Spherical path functions.
"""

import numpy as np
import scipy.stats
from via_sphere import MIN_LENGTH, distance_radians, Arc3d, \
    calculate_xtds, calculate_atds, calculate_distances, \
    calculate_bisector, to_array
from .trajectory_functions import find_most_extreme_value
from .SphereTurnArc import MIN_TURN_ANGLE, MAX_TURN_ANGLE
from .SpherePath import SpherePath

TWENTY_NM = np.deg2rad(1.0 / 3.0)
TWO_NM = np.deg2rad(1.0 / 30.0)
HALF_PI = np.pi / 2.0
MAX_LENGTH = np.pi - MIN_LENGTH

MINIMUM_ARC_LENGTH = np.deg2rad(0.1 / 60.0)
""" The minimum arc length in radians, 0.1 NM. """


def find_furthest_distance(points):
    """
    Find the distance (and index) of the furthest point from the start.

    Parameters
    ----------
    points: numpy array of Point3ds
        The points in spherical vector coordinates.

    Returns
    -------
    The distance and index of the furthest point from the first point.

    """
    distances = calculate_distances(points, points[0])
    return distances.max(), distances.argmax()


def find_extreme_point_along_track_index(arc, points, threshold):
    """
    Find the index of the point furthest along the Arc.

    Parameters
    ----------
    arc: Arc3d
        The Arc to compare the point to.

    points: numpy array of Point3ds
        The points in spherical vector coordinates.

    threshold: float
        The along track distance threshold [radians].

    Returns
    -------
    The index of the point furthest along the Arc if further than
    threshold from the start or end of the Arc, otherwise zero.

    """
    atds = calculate_atds(arc, points)
    max_atd = atds.max() - arc.length()
    min_atd = -atds.min()
    if max(min_atd, max_atd) > threshold:
        return atds.argmax() if min_atd < max_atd else atds.argmin()

    return 0


def find_extreme_point_index(points, first_index, last_index,
                             threshold, xtd_ratio, calc_along_track):
    """
    Find the index of the point in points furthest from the Arc.

    The points are searched between first_index and last_index.

    If the Arc is longer than MINIMUM_ARC_LENGTH, it finds the point with the
    largest across track distance. If the distance is larger than threshold
    or xtd_ratio time the arc length, it returns the index of the point.
    Otherwise, it calculates whether any points are beyond the end of the arc,
    if so it returns the index of the furthest point.

    If the Arc is not longer than MINIMUM_ARC_LENGTH, if finds the furthest point
    the start. If the distance from the point to the start and end points is
    greater than MINIMUM_ARC_LENGTH, it returns the index of the point.

    Parameters
    ----------
    points: numpy array of Point3ds
        The trajectory points in spherical vector coordinates.

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
        arc = Arc3d(points[first_index], points[last_index])
        # first point is after arc start
        if arc.length() > MINIMUM_ARC_LENGTH:
            # calculate cross track distances relative to the base arc
            xtds = calculate_xtds(arc, points[first_index + 1: last_index])
            max_xtd, xtd_index = find_most_extreme_value(xtds)
            xtd_index += 1
            # set the threshold to the minimum of the threshold or a
            # fraction of the arc length
            xtd_threshold = min(threshold, xtd_ratio * arc.length())
            xtd_threshold = max(xtd_threshold, MINIMUM_ARC_LENGTH)
            if (np.abs(max_xtd) > xtd_threshold):
                # if the point is further than the threshold, return it
                max_xtd_index = first_index + xtd_index
            elif calc_along_track:  # points are in-line
                # test whether a point is past the start or end of the arc
                atd_index = find_extreme_point_along_track_index(
                    arc, points[first_index: last_index], MINIMUM_ARC_LENGTH)
                if atd_index:
                    max_xtd_index = first_index + atd_index
        else:  # short arc
            # calculate the furthest point from the start point
            distance, xtd_index = \
                find_furthest_distance(points[first_index: last_index])
            if (distance > MINIMUM_ARC_LENGTH):
                # ensure that the point is far enough from the end point
                xtd_index += first_index
                end_distance = distance_radians(points[xtd_index],
                                                points[last_index])
                if end_distance > MINIMUM_ARC_LENGTH:
                    max_xtd_index = xtd_index

    return max_xtd_index


def find_extreme_point_indicies(points, threshold, *,
                                xtd_ratio=0.1, calc_along_track=False):
    """
    Find indicies of the most extreme points including the first and last points.

    Parameters
    ----------
    points: numpy array of Point3ds
        The trajectory points in spherical vector coordinates.

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
    finish_index = len(points) - 1
    start_index = 0
    indicies = np.zeros(1, dtype=int)

    if (2 < len(points)):
        # ensure that a point is further tha threshold from the start point
        distance, index = find_furthest_distance(points)
        if threshold < distance:
            # calculate the index of the most extreme point
            index = find_extreme_point_index(points, start_index,
                                             finish_index, threshold,
                                             xtd_ratio, calc_along_track)
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
                index = find_extreme_point_index(points, start_index,
                                                 last_index, threshold,
                                                 xtd_ratio, calc_along_track)

    indicies = np.append(indicies, finish_index)

    return indicies


def fit_arc_to_points(points, arc):
    """
    Calculate a closest arc through points.

    Note: there must be at least 2 points.

    Parameters
    ----------
    points: numpy array of Point3ds
        The points in spherical vector coordinates.

    arc: Arc3d
        An initial arc to match the ecef_points.

    Returns
    -------
    A closest arc through points, minimising their across track distances.

    """
    atds = calculate_atds(arc, points)
    xtds = calculate_xtds(arc, points)
    # calculate the slope and intercept of the closest line through the  points
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(atds, xtds)
    a = arc.perp_position(arc.a(), intercept)
    b = arc.perp_position(arc.b(), intercept + arc.length() * slope)
    return Arc3d(a, b)


def calculate_intersection(prev_arc, arc):
    """
    Calculate the intersection point between a pair of arcs.

    If the arcs are on (or very close to) the same Great Circle, it returns
    the start point of the second arc.

    Parameters
    ----------
    prev_arc, arc: Arc3ds
        The arcs before and after the intersection.

    Returns
    -------
    The intersection point of the arcs.

    """
    intersection = Arc3d(prev_arc.pole(), arc.pole())
    if MIN_LENGTH < intersection.length() < MAX_LENGTH:
        intersection_point = intersection.pole()
        # swap sign if intersection_point is antipodal point
        return -intersection_point \
            if distance_radians(arc.a(), intersection_point) > HALF_PI else \
            intersection_point
    else:
        return arc.a()


def calculate_max_turn_initiation_distance(in_length, out_length, *,
                                           max_distance=TWENTY_NM):
    """
    Calculate the maximum initation distance of a turn.

    Note: the default maximum intiation distance is 20 NM, see ICAO 9905
    AN/471 Required Navigation Performance Authorization

    Parameters
    ----------
    in_length, out_length: float
        The lengths of the arcs before and after the intersection [radians].

    max_distance : float
        The maximum permitted initation distance, default 20 NM [radians].

    Returns
    -------
    The maximum turn initation distance [radians].

    """
    return min(min(in_length, out_length) / 2, max_distance)


def calculate_turn_initiation_distance(prev_arc, arc, point,
                                       max_distance, threshold):
    """
    Calculate the turn initation distance from the arc legs and a point.

    Parameters
    ----------
    prev_arc: Arc3d
        The inbound path leg.

    arc: Arc3d
        The outbound path leg.

    point: Point3d
        A point between the inbound and outbound legs.

    max_distance : float
        The maximum turn initiation distance [radians].

    threshold : float
        The across track distance threshold [radians]

    Returns
    -------
    The turn initation distance [radians].

    """
    # Calculate the distance from the intersection to the point
    distance = distance_radians(arc.a(), point)
    if distance < max_distance:
        xtd_in = abs(prev_arc.cross_track_distance(point))
        xtd_out = abs(arc.cross_track_distance(point))

        # determine whether the point is close to either leg
        if (xtd_in > threshold) and (xtd_out > threshold):
            # calculate the bisector of the turn legs
            bisector = calculate_bisector(prev_arc, arc)
            xtd = abs(bisector.cross_track_distance(point))
            if xtd < distance:
                # calculate the angle from the bisector of the turn legs
                # Note: use arccos since the bisector is prependicular to pole
                angle = np.arccos(xtd / distance)
                half_turn_angle = abs(prev_arc.turn_angle(arc.b())) / 2
                # calculate the turn radius
                cos_angle = np.cos(angle)
                cos_half_turn_angle = np.cos(half_turn_angle)
                sin2_half_turn_angle = 1 - cos_half_turn_angle ** 2
                # ensure that factor is never negative for sqrt
                factor = max(cos_angle ** 2 - sin2_half_turn_angle, 0.0)
                radius = distance * cos_half_turn_angle * \
                    (cos_angle + np.sqrt(factor)) / sin2_half_turn_angle

                # Calculate turn initiation distance from the radius
                distance = radius * np.tan(half_turn_angle)

    return min(distance, max_distance)


def derive_horizontal_path(points, threshold, calc_along_track=False):
    """
    Derive horizontal path waypoints and turn anticipation distances from points.

    Parameters
    ----------
    points: numpy array of Point3ds
        The trajectory points in spherical vector coordinates.

    threshold: float
        The across track distance threshold [radians].

    calc_along_track : Boolean
        Calculate the along track distance, default False.

    Returns
    -------
    The SpherePath between the points.

    """
    # Find extreme points and their indicies in the ecef_points array
    indicies = find_extreme_point_indicies(points, threshold,
                                           calc_along_track=calc_along_track)
    extreme_points = points[[indicies]]

    # Calculate the Great Circle arc along the first route leg
    prev_index = 0
    index = indicies[1]
    prev_arc = Arc3d(extreme_points[0], extreme_points[1])
    prev_arc = fit_arc_to_points(points[prev_index: index + 1], prev_arc)

    # Create lists for the waypoints and turn initiation distances
    # Starting with the first point
    path_waypoints = [prev_arc.a()]
    turn_distances = [0.0]

    prev_length = prev_arc.length()
    for i in range(1, len(extreme_points) - 1):
        # Calculate the Great Circle arc along the next route leg
        prev_index = index
        index = indicies[i + 1]
        arc = Arc3d(extreme_points[i], extreme_points[i + 1])
        arc = fit_arc_to_points(points[prev_index: index + 1], arc)

        # Calculate the turn parameters at the waypoint
        turn_angle = prev_arc.turn_angle(arc.b())
        max_turn_distance = calculate_max_turn_initiation_distance(prev_length, arc.length())

        waypoint = arc.a()
        turn_distance = 0.0

        # Determine whether the turn is valid, calculate waypoint and
        # turn initiation distance accordingly
        is_valid_turn = (MIN_TURN_ANGLE < abs(turn_angle) <= MAX_TURN_ANGLE) and \
            (max_turn_distance > TWO_NM)
        if is_valid_turn:
            waypoint = calculate_intersection(prev_arc, arc)
            turn_distance = calculate_turn_initiation_distance(prev_arc, arc,
                                                               points[prev_index + 1],
                                                               max_turn_distance,
                                                               threshold / 4.0)
        path_waypoints.append(waypoint)
        turn_distances.append(turn_distance)

        prev_arc = arc
        prev_length = arc.length()

    # Add the last point
    path_waypoints.append(prev_arc.b())
    turn_distances.append(0.0)

    return SpherePath(to_array(path_waypoints), np.array(turn_distances))
