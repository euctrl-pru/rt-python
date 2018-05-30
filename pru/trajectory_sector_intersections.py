# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to find trajectory sector intersection data.
"""

import pandas as pd
from .AirspaceVolume import AirspaceVolume
from .gis_database_interface import find_2D_airspace_intersections, \
    get_elementary_airspace_name, get_elementary_airspace_altitude_range, \
    NotFoundException
from .airspace_intersections import find_3D_airspace_intersections
from pru.logger import logger

log = logger(__name__)


def find_trajectory_sector_intersections(smooth_traj):
    """
    Find airspace sector intersection positions from a smoothed trajectory.

    Parameters
    ----------
    smooth_traj: SmoothedTrajectory
        A SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    Returns
    -------
    intersection_positions: a pandas DataFrame
        The trajectory user airspace intersection positions.
        Empty if no intersections found.
    """
    lats = []
    lons = []
    volume_ids = []

    min_altitude = smooth_traj.altp.altitudes.min()
    max_altitude = smooth_traj.altp.altitudes.max()
    lats, lons, volume_ids = find_2D_airspace_intersections(smooth_traj.flight_id,
                                                            smooth_traj.path.lats,
                                                            smooth_traj.path.lons,
                                                            min_altitude, max_altitude)
    if len(lats):
        # A dict to hold the intersected volumes
        volumes = {}
        try:
            for volume_id in set(volume_ids):
                volume_name = get_elementary_airspace_name(volume_id)
                bottom_alt, top_alt = get_elementary_airspace_altitude_range(volume_id)
                volumes.setdefault(volume_id, AirspaceVolume(volume_name,
                                                             bottom_alt, top_alt))
        except NotFoundException:
            log.exception('sector id: %s not found for flight id: %s',
                          volume_id, smooth_traj.flight_id)
            return pd.DataFrame()

        return find_3D_airspace_intersections(smooth_traj, lats, lons,
                                              volume_ids, volumes)
    else:
        return pd.DataFrame()
