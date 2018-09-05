# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory airport intersection data.
"""
import numpy as np
import pandas as pd
from via_sphere import calculate_distances, latitude, longitude, \
    distance_radians, EPSILON, Arc3d
from .trajectory_functions import rad2nm, calculate_value_reference, \
    calculate_descending_value_reference, calculate_date_times

AIRPORT_INTERSECTION_FIELD_LIST = ['FLIGHT_ID', 'AIRPORT_ID', 'RADIUS', 'IS_DESTINATION',
                                   'LAT', 'LON', 'ALT', 'TIME', 'DISTANCE']

DEFAULT_RADIUS = 40.0
'The default airport cylinder radius in [Nautical Miles].'

DEFAULT_DISTANCE_TOLERANCE = 0.25
""" The default distance tolerance in Nautical Miles, 0.25 NM. """


def find_cylinder_intersection_index(points, centre, radius, is_destination):
    """
    Find the index and ratio in points at radius from centre.

    Parameters
    ----------
    points: numpy array of Point3ds
        An array of points representing a horizontal aircraft trajectory.

    centre: Point3d
        The centre of the cylinder.

    radius: float
        The radius of the cylinder [radians].

    is_destination: Boolean
        True if the cylinder is for a destination airport, False if it's
        a departure airport.

    Returns
    -------
    The index and ratio along the array of Point3ds of the cylinder
    intersection point. The index is -1 if there was no intersection.

    """
    # Calculate distances of the points from the centre of the cylinder
    distances = calculate_distances(points, centre)

    # if the points intersect the cylinder
    min_distance = distances.min()
    max_distance = distances.max()
    if min_distance < radius < max_distance:
        return calculate_descending_value_reference(distances, radius) \
            if is_destination else calculate_value_reference(distances, radius)

    return -1, 0.0


def find_airport_intersection(smooth_traj, traj_path, airport,
                              ref_point, radius, is_destination,
                              distance_tolerance=DEFAULT_DISTANCE_TOLERANCE):
    """
    Find an airport cylinder intersection position from a smoothed trajectory.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the SmoothedTrajectory.

    airport: string
        The ICAO id of the airport.

    ref_point: Point3D
        The reference point of the airport.

    radius: float
        The radius of the cylinder around the airport [Nautical Miles].

    is_destination: Boolean
        True if the cylinder is for a destination airport, False if it's
        a departure airport.

    distance_tolerance: float
        The tolerance for path and cylinder distances [Nautical Miles].

    Returns
    -------
    A pandas DataFrame containing the airport cylinder intersection position data.
    Or an empty DataFrame, if not found.

    """
    radius_radians = np.deg2rad(radius / 60.0)
    tolerance_radians = np.deg2rad(distance_tolerance / 60.0)
    path_points = traj_path.points
    index, ratio = find_cylinder_intersection_index(path_points,
                                                    ref_point, radius_radians,
                                                    is_destination)
    if index < 0:  # no intersections found
        return pd.DataFrame()

    int_point = path_points[index]

    # Calculate the precise intersection point
    distance = radius_radians
    if (ratio > 0.0) and (index < len(path_points) - 1):
        # Calculate the along and across track distances to the centre
        arc = Arc3d(int_point, path_points[index + 1])
        atd = arc.along_track_distance(ref_point)
        xtd = np.abs(arc.cross_track_distance(ref_point))

        d = radius_radians if xtd < radius_radians else 0.0
        if d and (xtd > EPSILON):
            # project the radius on to the arc using spherical Pythagoras
            d = np.arccos(np.cos(d) / np.cos(xtd))

        if is_destination:
            d = atd + d if (atd + d) <= arc.length() else atd - d
        else:
            d = atd - d if (atd - d) >= 0.0 else atd + d
        int_point = arc.position(d)
        distance = distance_radians(int_point, ref_point)

    # Don't return result if distance is invalid
    distance_nm = rad2nm(distance)
    if np.abs(distance_nm - radius) > distance_tolerance:
        flight_id = smooth_traj.flight_id
        raise ValueError(f'Distance not within tolerance, {flight_id}, {distance_nm}')

    # Create an array of flight_ids
    flight_id = np.array([smooth_traj.flight_id])

    # Create an array of airport_ids
    airport_id = np.array([airport])

    # radii = np.array([distance_nm])
    radii = np.array([radius])

    lats = np.array([latitude(int_point)])
    lons = np.array([longitude(int_point)])

    is_destination = np.ones(1, dtype=np.bool) if is_destination else \
        np.zeros(1, dtype=np.bool)

    distances = rad2nm(traj_path.calculate_path_distances([int_point],
                                                          tolerance_radians))
    alts = smooth_traj.altp.interpolate(distances)

    times = smooth_traj.timep.interpolate_by_distance(distances)
    date_times = calculate_date_times(times, smooth_traj.timep.start_time)

    return pd.DataFrame({'FLIGHT_ID': flight_id,
                         'AIRPORT_ID': airport_id,
                         'RADIUS': radii,
                         'IS_DESTINATION': is_destination,
                         'LAT': lats,
                         'LON': lons,
                         'ALT': alts,
                         'TIME': date_times,
                         'DISTANCE': distances},
                        columns=AIRPORT_INTERSECTION_FIELD_LIST)
