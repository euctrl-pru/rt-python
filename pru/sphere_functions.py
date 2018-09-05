# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports Spherical Vector coordinates.
"""

from via_sphere import Arc3d, calculate_Arc3ds, calculate_closest_distances


def calculate_position(points, index, ratio=0.0):
    """
    Calculate the position of a point at index and ratio along a list of Point3ds.

    Parameters
    ----------
    points: Point3ds array
        An array of Point3ds.

    index: integer
        The index of the point, or the point before if ratio > 0.0

    ratio: ratio
        The ratio of the position after the point at index, default 0.0.
        0.0 <= ratio < 1.0

    Returns
    -------
    The Point3d at index and ratio along the Point3ds array.

    """
    point = points[index]
    if ratio > 0.0:
        if index < len(points) - 1:
            arc = Arc3d(point, points[index + 1])
            point = arc.position(ratio * arc.length())
        else:
            point = points[-1]

    return point


def find_index_and_ratio(points, point):
    """
    Calculate the  index and ratio of the closest point along points to point.

    Parameters
    ----------
    points: numpy array of Point3ds
        The trajectory points in spherical vector coordinates.

    point: Point3d
        The point to find the closest point to.

    Returns
    -------
    The index and ratio of the closest point along the Point3ds array.

    """
    # Calculate the closest distances of the point to the legs between points
    arcs = calculate_Arc3ds(points)
    distances = calculate_closest_distances(arcs, point)

    # The index of the closest leg
    index = distances.argmin()

    # Calculate the ratio along the closest leg
    arc = Arc3d(points[index], points[index + 1])
    atd = arc.along_track_distance(point)
    ratio = atd / arc.length()

    # if the closest point is at the end of the leg, use start of next leg
    if ratio >= 1.0:
        ratio = 0.0
        index += 1

    return index, ratio
