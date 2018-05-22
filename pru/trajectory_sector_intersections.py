# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory sector intersection data.
"""

import numpy as np
import pandas as pd
from .EcefPoint import rad2nm
from .ecef_functions import calculate_EcefPoints
from .SmoothedTrajectory import SmoothedTrajectory
from .trajectory_functions import calculate_date_times, set_exit_flags
from .trajectory_interpolation import interpolate_altitude_profile, \
    interpolate_time_profile_by_distance
from .gis_database_interface import find_2D_airspace_intersections

AIRSPACE_INTERSECTION_FIELD_LIST = ['FLIGHT_ID', 'SECTOR_ID', 'IS_EXIT',
                                    'LAT', 'LON', 'ALT', 'TIME', 'DISTANCE']
""" The output intersection fields. """


def find_trajectory_sector_intersections(smooth_traj):
    """
    Find airspace sector intersection positions from a smoothed trajectory

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The trajectory sector intersection positions.
    """
    lats = []
    lons = []
    sector_ids = []

    min_altitude = smooth_traj.altp.altitudes.min()
    max_altitude = smooth_traj.altp.altitudes.max()
    lats, lons, sector_ids = find_2D_airspace_intersections(smooth_traj.flight_id,
                                                            smooth_traj.path.lats,
                                                            smooth_traj.path.lons,
                                                            min_altitude, max_altitude)
    # Create an array of flight_ids
    flight_id = np.array(len(lats), dtype='object')
    flight_id.fill(str(smooth_traj.flight_id))

    alts = np.zeros(len(lats), dtype=np.float)
    date_times = np.empty(len(lats), dtype='datetime64[us]')
    date_times.fill(smooth_traj.timep.start_time)

    is_exits = set_exit_flags(sector_ids)

    distances = np.zeros(len(lats), dtype=np.float)

    # create a pandas DataFrame with trajectory_fields.AIRSPACE_INTERSECTION_FIELD_LIST
    intersect_df = pd.DataFrame({'FLIGHT_ID': flight_id,
                                 'SECTOR_ID': np.array(sector_ids),
                                 'IS_EXIT': is_exits,
                                 'LAT': np.array(lats),
                                 'LON': np.array(lons),
                                 'ALT': alts,
                                 'TIME': date_times,
                                 'DISTANCE': distances},
                                columns=AIRSPACE_INTERSECTION_FIELD_LIST)

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
        intersect_df['ALT'] = interpolate_altitude_profile(smooth_traj.altp, sorted_distances)
        times = interpolate_time_profile_by_distance(smooth_traj.timep, sorted_distances)
        intersect_df['TIME'] = calculate_date_times(times, smooth_traj.timep.start_time)

    # return the data in a pandas DataFrame with trajectory_fields.AIRSPACE_INTERSECTION_FIELD_LIST
    return intersect_df
