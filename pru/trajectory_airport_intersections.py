# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory airport intersection data.
"""

import numpy as np
import pandas as pd
from .EcefPoint import rad2nm
from .ecef_functions import calculate_EcefPoints
from .SmoothedTrajectory import SmoothedTrajectory
from .trajectory_functions import calculate_date_times
from .trajectory_interpolation import interpolate_time_profile_by_distance
from .gis_database_interface import find_airport_cylinder_intersection

AIRPORT_INTERSECTION_FIELD_LIST = ['FLIGHT_ID', 'AIRPORT_ID', 'RADIUS', 'IS_DESTINATION',
                                   'LAT', 'LON', 'ALT', 'TIME', 'DISTANCE']

DEFAULT_RADIUS = 110.0
'The default airport cylinder radius in [Nautical Miles].'


def find_airport_intersection(smooth_traj, airport, radius, is_destination):
    """
    Find an airport cylinder intersection position from a smoothed trajectory

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    airport_id: string
        The minimum altitude of the positions [feet].

    radius: float
        The maximum altitude of the positions [Nautical Miles].

    Returns
    -------
    An array containing the airport cylinder intersection position data.
    Or None, if not found.

    """
    lats = []
    lons = []
    lats, lons = find_airport_cylinder_intersection(smooth_traj.flight_id,
                                                    smooth_traj.path.lats,
                                                    smooth_traj.path.lons,
                                                    airport, radius,
                                                    is_destination)

    # Create an array of flight_ids
    flight_id = np.array(len(lats), dtype='object')
    flight_id.fill(str(smooth_traj.flight_id))

    # Create an array of airport_ids
    airport_id = np.array(len(lats), dtype='object')
    airport_id.fill(airport)

    radii = np.zeros(len(lats), dtype=np.float)
    radii.fill(radius)

    is_destination = np.ones(len(lats), dtype=np.bool) if is_destination else \
        np.zeros(len(lats), dtype=np.bool)

    alts = np.zeros(len(lats), dtype=np.float)
    date_times = np.empty(len(lats), dtype='datetime64[us]')
    date_times.fill(smooth_traj.timep.start_time)

    distances = np.zeros(len(lats), dtype=np.float)

    intersect_df = pd.DataFrame({'FLIGHT_ID': flight_id,
                                 'AIRPORT_ID': airport_id,
                                 'RADIUS': radii,
                                 'IS_DESTINATION': is_destination,
                                 'LAT': np.array(lats),
                                 'LON': np.array(lons),
                                 'ALT': alts,
                                 'TIME': date_times,
                                 'DISTANCE': distances},
                                columns=AIRPORT_INTERSECTION_FIELD_LIST)

    if (len(lats)):

        # Construct the EcefPath corresponding to the HorizontalPath
        ecef_path = smooth_traj.path.ecef_path()
        tolerance_radians = np.deg2rad(0.25 / 60.0)
        ecef_points = calculate_EcefPoints(intersect_df['LAT'].values,
                                           intersect_df['LON'].values)
        path_distances = rad2nm(ecef_path.calculate_path_distances(ecef_points,
                                                                   tolerance_radians))
        # Sort dataframe by path_distances
        intersect_df['DISTANCE'] = path_distances
        intersect_df.sort_values(by=['DISTANCE'], inplace=True)

        sorted_distances = intersect_df['DISTANCE'].values
        intersect_df['ALT'] = smooth_traj.altp.interpolate(sorted_distances)
        times = interpolate_time_profile_by_distance(smooth_traj.timep, sorted_distances)
        intersect_df['TIME'] = calculate_date_times(times, smooth_traj.timep.start_time)

    # return the data in a pandas DataFrame with trajectory_fields.AIRSPACE_INTERSECTION_FIELD_LIST
    return intersect_df
