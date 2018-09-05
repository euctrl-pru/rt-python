# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory airspace intersection data.
"""

import numpy as np
import pandas as pd
from via_sphere import calculate_latitudes, calculate_longitudes
from .trajectory_functions import calculate_value_reference, calculate_date_times, \
    rad2nm

AIRSPACE_INTERSECTION_FIELD_LIST = ['FLIGHT_ID', 'SECTOR_ID', 'IS_EXIT',
                                    'LAT', 'LON', 'ALT', 'TIME', 'DISTANCE']
""" The output intersection fields. """

INITIAL_POSITION_TOLERANCE = 0.01
""" The tolerance  of an initial position from the start of a trajectory. """

DEFAULT_ACROSS_TRACK_TOLERANCE = 0.5


def set_exit_flags(ids):
    """
    Set flags corresponding to the input ids.

    Parameters
    ----------
    ids: ids array
        An array of ids.

    Returns
    -------
    A numpy boolean array with each value set for the second occurance of an id.

    """
    is_exits = np.zeros(len(ids), dtype=np.bool)
    if len(ids):
        # A dict to hold volume entry indicies
        entry_indicies = set()

        for index, volume_id in enumerate(ids):
            if volume_id in entry_indicies:
                entry_indicies.remove(volume_id)
                is_exits[index] = True
            else:
                # save this index as the entry index for this volume
                entry_indicies.add(volume_id)

    return is_exits


def calculate_2D_intersection_distances(traj_path, intersection_points,
                                        volume_ids, start_distance,
                                        across_track_tolerance=DEFAULT_ACROSS_TRACK_TOLERANCE):
    """
    Calculate path distances to intersection_points.

    Parameters
    ----------
    traj_path : an EcefPath
        The EcefPath of the trajectory.

    intersection_points: array of EcefPoints
        The horizontal intersection points.

    volume_ids: list of strings
        The ids of the volumes intersected at the positions.

    start_distance: float
        The distance along the path to the start of the trajectory section,
        default zero [Nautical Miles].

    across_track_tolerance: float
        The maximum across track distance to find path distances [Nautical Miles].

    Returns
    -------
    A pandas Dataframe with sector ids and distances.

    """
    start_index = 0
    if start_distance:
        distances_nm = rad2nm(traj_path.path_distances())
        start_index, _ = calculate_value_reference(distances_nm, start_distance)

    tolerance_radians = np.deg2rad(across_track_tolerance / 60.0)
    distances_2d = rad2nm(traj_path.calculate_path_distances(intersection_points,
                                                             tolerance_radians,
                                                             index=start_index))
    df_2d = pd.DataFrame({'SECTOR_ID': np.array(volume_ids),
                          'DISTANCE': distances_2d})
    return df_2d.sort_values(by=['DISTANCE'])


def calculate_3D_intersection_distances(alt_p, volume_id, airspace_volume,
                                        entry_distance, exit_distance,
                                        entry_altitude, exit_altitude,
                                        include_horizontal_exit):
    """
    Calculate path distances where an AltitudeProfile intersects an AirspaceVolume.

    Note: this function calculates vertical intersections and determines
    whether horizontal intersections are valid considering the vertical range
    of the airspace_volume.

    Parameters
    ----------
    alt_p: AltitudeProfile
        The altitude profile of the flight.

    volume_id: string
        The id of the airspace volume.

    airspace_volume: AirspaceVolume
        The airspace volume.

    entry_distance, exit_distance: floats
        The horizontal entry and exit distances [Nautical Miles].

    entry_altitude, exit_altitude: floats
        The altitudes at the horizontal entry and exit distances [feet].

    include_horizontal_exit: bool
        A flag to indicate if horizontal exit distances are required.

    Returns
    -------
    distances: an array of floats
        The unordered intersection distances [Nautical Miles].
        Empty if no intersections found.

    """
    distances = []

    min_alt, max_alt = alt_p.altitude_range(entry_distance, exit_distance)
    if airspace_volume.vertical_intersection(min_alt, max_alt):
        # is the horizontal entry intersection valid?
        if airspace_volume.is_inside(entry_altitude):
            distances.append(entry_distance)

        # if there are vertical intersections with the bottom of the airspace volume
        if airspace_volume.bottom_intersection(min_alt, max_alt):
            distances.extend(alt_p.intersection_distances(airspace_volume.bottom_altitude,
                                                          entry_distance, exit_distance))

        # if there are vertical intersections with the top of the airspace volume
        if airspace_volume.top_intersection(min_alt, max_alt):
            distances.extend(alt_p.intersection_distances(airspace_volume.top_altitude,
                                                          entry_distance, exit_distance))

        # is the horizontal exit intersection valid?
        if include_horizontal_exit and airspace_volume.is_inside(exit_altitude):
            distances.append(exit_distance)

    return distances


def calculate_3D_intersections(alt_p, volumes, df_2d):
    """
    Calculate path distances where an AltitudeProfile intersects AirspaceVolume.

    Note: this function calculates vertical intersections and determines
    whether horizontal intersections are valid considering the vertical range
    of the airspace_volume.

    Parameters
    ----------
    alt_p: AltitudeProfile
        The altitude profile of the flight.

    volumes: dict of AirspaceVolume
        The airspace volumes.

    df_2d: pandas DataFrame
        The pandas DataFrame of horizontal airspace sector intersections.

    Returns
    -------
    df_3d: a pandas DataFrame
        The sorted 3D trajectory intersection distances and sector ids.
        Empty if no 3D intersections found.

    """
    distances_3d = []
    ids_3d = []

    ids_2d = df_2d['SECTOR_ID'].values
    distances_2d = df_2d['DISTANCE'].values

    altitudes_2d = alt_p.interpolate(distances_2d)

    # A dict to hold volume entry indicies
    entry_indicies = {}

    # loop around the horizontal intersections
    for index in range(len(distances_2d)):
        volume_id = ids_2d[index]

        # if entry found for this sector
        if volume_id in entry_indicies:
            # save the entry index and remove the entry from entry_indicies
            entry_index = entry_indicies[volume_id]
            del entry_indicies[volume_id]

            # Get the horizontal entry and exit distances and altitudes
            entry_distance = distances_2d[entry_index]
            entry_altitude = altitudes_2d[entry_index]

            exit_index = index
            exit_distance = distances_2d[exit_index]
            exit_altitude = altitudes_2d[exit_index]

            # Calculate all the 3D intersection distances with the airspace volume
            # Note: distances may not be in ascending order.
            airspace_volume = volumes[volume_id]
            distances = calculate_3D_intersection_distances(alt_p, volume_id, airspace_volume,
                                                            entry_distance, exit_distance,
                                                            entry_altitude, exit_altitude,
                                                            include_horizontal_exit=True)
            if len(distances):  # if this volume has intersections
                distances_3d.extend(distances)
                ids_3d.extend([volume_id] * len(distances))

        else:  # volume entry index not found
            # save this index as the entry index for this volume
            entry_indicies[volume_id] = index

    # any remaining sections finish at the end of the trajectory
    finish_distance = alt_p.distances[-1]
    finish_altitude = alt_p.altitudes[-1]

    # iterate through remaining entry_indicies
    for volume_id, entry_index in entry_indicies.items():
        entry_distance = distances_2d[entry_index]
        entry_altitude = altitudes_2d[entry_index]

        # Calculate 3D intersection distances with the airspace volume
        # Note: it does not include the last horizontal exit distance since
        # that is the end of the trajectory and not an intersection.
        airspace_volume = volumes[volume_id]
        distances = calculate_3D_intersection_distances(alt_p, volume_id, airspace_volume,
                                                        entry_distance, finish_distance,
                                                        entry_altitude, finish_altitude,
                                                        include_horizontal_exit=False)
        if len(distances):  # if this volume has intersections
            distances_3d.extend(distances)
            ids_3d.extend([volume_id] * len(distances))

    # return the ids and distances in a pandas dataframe in ascending distance order.
    if len(distances_3d):
        df_3d = pd.DataFrame({'SECTOR_ID': np.array(ids_3d),
                              'DISTANCE': np.array(distances_3d)})
        return df_3d.sort_values(by=['DISTANCE'])
    else:  # no 3D intersections found
        return pd.DataFrame()


def find_3D_airspace_intersections(smooth_traj, traj_path,
                                   intersection_points, volume_ids, volumes,
                                   start_distance=0.0, is_cruising=False):
    """
    Find 3D airspace intersection positions for a smoothed trajectory.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the trajectory.

    intersection_points: array of EcefPoints
        The horizontal intersection points.

    volume_ids: list of strings
        The ids of the volumes intersected at the positions.

    volumes: dict of AirspaceVolume
        The AirspaceVolumes intersected by the SmoothedTrajectory.

    start_distance: float
        The distance along the path to the start of the trajectory section,
        default zero [Nautical Miles].

    is_cruising : Boolean
        Whether the intersections were found in a cruising section,
        default False.

    Returns
    -------
    intersect3d_df: a pandas DataFrame
        The 3D trajectory intersection positions.
        Empty if no intersections found.

    """
    # Construct the EcefPath corresponding to the HorizontalPath
    df_2d = calculate_2D_intersection_distances(traj_path, intersection_points,
                                                volume_ids, start_distance)

    # No need to calculate 3D intersections for cruising flights
    df_3d = df_2d if is_cruising else \
        calculate_3D_intersections(smooth_traj.altp, volumes, df_2d)
    if df_3d.shape[0] == 0:
        return df_3d

    # Set sector exit flags
    df_3d['IS_EXIT'] = set_exit_flags(df_3d['SECTOR_ID'].values)

    # Remove initial positions
    initial_position_distance = start_distance + INITIAL_POSITION_TOLERANCE
    initial_positions = (df_3d['DISTANCE'] < initial_position_distance)
    df_3d = df_3d[~initial_positions]

    distances_3d = df_3d['DISTANCE'].values
    count = len(distances_3d)
    if count == 0:
        return df_3d

    # Create an array of flight_ids for the pandas Dataframe
    flight_id = np.array(count, dtype='object')
    flight_id.fill(str(smooth_traj.flight_id))

    # Convert the sector ids to sector names
    volume_ids = df_3d['SECTOR_ID'].values
    sector_names = [volumes.get(item).name for item in volume_ids]

    # Calculate intersection Lat Longs
    intersection_positions = traj_path.calculate_positions(distances_3d)
    lats_3d = calculate_latitudes(intersection_positions)
    lons_3d = calculate_longitudes(intersection_positions)

    # Calculate intersection altitudes
    altitudes = smooth_traj.altp.interpolate(distances_3d)

    # Calculate the pandas date_times
    times = smooth_traj.timep.interpolate_by_distance(distances_3d)
    date_times = calculate_date_times(times, smooth_traj.timep.start_time)

    # return the data in a pandas DataFrame with fields AIRSPACE_INTERSECTION_FIELD_LIST
    return pd.DataFrame({'FLIGHT_ID': flight_id,
                         'SECTOR_ID': np.array(sector_names),
                         'IS_EXIT': df_3d['IS_EXIT'].values,
                         'LAT': lats_3d,
                         'LON': lons_3d,
                         'ALT': altitudes,
                         'TIME': date_times,
                         'DISTANCE': distances_3d},
                        columns=AIRSPACE_INTERSECTION_FIELD_LIST)
