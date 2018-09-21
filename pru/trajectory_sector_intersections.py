# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory sector intersection data.
"""

import numpy as np
import pandas as pd
from via_sphere import global_Point3d, calculate_latitudes, calculate_longitudes
from .AirspaceVolume import AirspaceVolume
from .gis_database_interface import find_horizontal_sector_intersections, \
    get_elementary_airspace_name, get_elementary_airspace_altitude_range, \
    NotFoundException
from .airspace_intersections import find_3D_airspace_intersections
from pru.logger import logger

log = logger(__name__)


def find_trajectory_section_sector_intersections(smooth_traj, traj_path,
                                                 min_altitude, max_altitude,
                                                 start_distance, finish_distance):
    """
    Find sector intersection positions for a section of a smoothed trajectory.

    It calls find_horizontal_sector_intersections to find horizontal intersections
    for the trajectory section between start_distance and finish_distance.

    If horizontal intersections are found, find_3D_airspace_intersections is
    called to find vertical intersections corresponding to the horizontal
    intersections.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the SmoothedTrajectory.

    min_altitude: int
        The minimum altitude of the trajectory section [feet].

    max_altitude: int
        The maximum altitude of the trajectory section [feet].

    start_distance: float
        The distance along the path to the start of the trajectory section
        [Nautical Miles].

    finish_distance: float
        The distance along the path to the end of the trajectory section
        [Nautical Miles].

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The trajectory user airspace intersection positions.
        Empty if no intersections found.

    """
    lats = []
    lons = []
    volume_ids = []

    positions = traj_path.subsection_positions(start_distance, finish_distance)
    path_lats = calculate_latitudes(positions)
    path_lons = calculate_longitudes(positions)
    lats, lons, volume_ids = find_horizontal_sector_intersections(smooth_traj.flight_id,
                                                                  path_lats, path_lons,
                                                                  int(min_altitude),
                                                                  int(max_altitude))
    if len(lats):
        # A dict to hold the intersected volumes
        volumes = {}
        is_cruising = (min_altitude == max_altitude)
        try:
            for volume_id in set(volume_ids):
                volume_name = get_elementary_airspace_name(volume_id)
                bottom_alt = 0
                top_alt = 0
                if not is_cruising:
                    bottom_alt, top_alt = get_elementary_airspace_altitude_range(volume_id)
                volumes.setdefault(volume_id, AirspaceVolume(volume_name,
                                                             bottom_alt, top_alt))
        except NotFoundException:
            log.exception('sector id: %s not found for flight id: %s',
                          volume_id, smooth_traj.flight_id)
            return pd.DataFrame()

        intersection_points = global_Point3d(np.array(lats), np.array(lons))
        return find_3D_airspace_intersections(smooth_traj, traj_path,
                                              intersection_points,
                                              volume_ids, volumes, start_distance,
                                              is_cruising)
    else:
        return pd.DataFrame()


def find_climbing_sector_intersections(smooth_traj, traj_path):
    """
    Find airspace sector intersections for a climbing trajectory section.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the SmoothedTrajectory.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The climbing trajectory user airspace intersection positions.
        Empty if no intersections found.

    """
    toc_distance = smooth_traj.altp.top_of_climb_distance()
    if toc_distance:
        min_altitude = smooth_traj.altp.altitudes[0]
        max_altitude = smooth_traj.altp.altitudes.max()
        return find_trajectory_section_sector_intersections(smooth_traj,
                                                            traj_path,
                                                            min_altitude, max_altitude,
                                                            0.0, toc_distance)
    else:
        return pd.DataFrame()


def find_cruising_sector_intersections(smooth_traj, traj_path):
    """
    Find airspace sector intersections for a cruising trajectory section.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the SmoothedTrajectory.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The cruising trajectory user airspace intersection positions.
        Empty if no intersections found.

    """
    toc_distance = smooth_traj.altp.top_of_climb_distance()
    tod_distance = smooth_traj.altp.top_of_descent_distance()
    if toc_distance < tod_distance:
        altitude = smooth_traj.altp.altitudes.max()
        return find_trajectory_section_sector_intersections(smooth_traj,
                                                            traj_path,
                                                            altitude, altitude,
                                                            toc_distance, tod_distance)
    else:
        return pd.DataFrame()


def find_descending_sector_intersections(smooth_traj, traj_path):
    """
    Find airspace sector intersections for a descending trajectory section.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    traj_path : an EcefPath
        The EcefPath of the SmoothedTrajectory.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The descending trajectory user airspace intersection positions.
        Empty if no intersections found.

    """
    tod_distance = smooth_traj.altp.top_of_descent_distance()
    end_distance = smooth_traj.altp.distances[-1]
    if tod_distance < end_distance:
        max_altitude = smooth_traj.altp.altitudes.max()
        min_altitude = smooth_traj.altp.altitudes[-1]
        return find_trajectory_section_sector_intersections(smooth_traj,
                                                            traj_path,
                                                            min_altitude, max_altitude,
                                                            tod_distance, end_distance)
    else:
        return pd.DataFrame()


def find_trajectory_sector_intersections(smooth_traj):
    """
    Find airspace sector intersection positions from a smoothed trajectory.

    It finds intersections in three sections corresponding to the: climbing,
    cruising and desending sections of a trajectory.

    The resulting intersections are the concatenation of the climbing,
    cruising and desending intersections.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The trajectory airspace sector intersection positions.
        Empty if no intersections found.

    """
    traj_path = smooth_traj.path.ecef_path()
    intersections = find_climbing_sector_intersections(smooth_traj, traj_path)

    cruise_intersections = find_cruising_sector_intersections(smooth_traj, traj_path)
    if not cruise_intersections.empty:
        intersections = cruise_intersections if intersections.empty else \
            pd.concat([intersections, cruise_intersections], ignore_index=True)

    descent_intersections = find_descending_sector_intersections(smooth_traj, traj_path)
    if not descent_intersections.empty:
        intersections = descent_intersections if intersections.empty else \
            pd.concat([intersections, descent_intersections], ignore_index=True)

    return intersections
