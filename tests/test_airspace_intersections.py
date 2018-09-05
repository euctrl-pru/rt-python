#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from via_sphere import global_Point3d
from pru.AltitudeProfile import AltitudeProfile
from pru.AirspaceVolume import AirspaceVolume
from pru.HorizontalPath import HorizontalPath
from pru.TimeProfile import TimeProfile
from pru.SmoothedTrajectory import SmoothedTrajectory
from pru.airspace_intersections import *

NM = 1.0  # np.deg2rad(1.0 / 60.0)

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 5400.,
                      6000., 6000., 6000.,
                      6000., 5400., 4200.])

DISTANCES = np.array([0., 5 * NM, 10 * NM,
                      15 * NM, 20 * NM, 25 * NM,
                      30 * NM, 35 * NM, 40 * NM,
                      45 * NM, 50 * NM, 55 * NM])

ALTITUDE_PROFILE = AltitudeProfile(DISTANCES, ALTITUDES)

SECTORS = {'1': AirspaceVolume('one', 0, 3500),
           '2': AirspaceVolume('two', 3500, 5500),
           '3': AirspaceVolume('three', 5500, 10000)}

ROUTE_LATS = np.array([0., 5. / 60., 10 / 60.,
                       15 / 60., 20 / 60., 25 / 60.,
                       30 / 60., 35 / 60., 40 / 60.,
                       45 / 60., 50 / 60., 55 / 60.])

ROUTE_LONS = np.zeros(12, dtype=float)
TURN_DISTANCES = np.zeros(12, dtype=float)

START_TIME = np.datetime64('2017-08-01T08:47:31.000')

ELAPSED_TIMES = np.array([0.,   292.,   718.,
                          2543.,  2573.,  2603.,
                          2633.,  2663.,  2693.,
                          2723.,  2753.,  2759.])


class TestAirspaceIntersections(unittest.TestCase):

    def test_set_exit_flags(self):
        """Test the set_exit_flags function."""
        ids_1 = ['A', 'A', 'B', 'B', 'C', 'B', 'C']
        exits = np.array([False, True, False, True, False, False, True])

        result = set_exit_flags(ids_1)
        assert_array_almost_equal(result, exits)

    def test_calculate_2D_intersection_distances(self):
        path_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)

        LATS = np.array([20. / 60.,  40. / 60., 60. / 60.])
        LONS = np.zeros(3, dtype=float)
        intersection_points = global_Point3d(LATS, LONS)
        sector_ids = ['2', '3', '1']
        start_distance = 0.
        distances_1 = calculate_2D_intersection_distances(path_0.ecef_path(),
                                                          intersection_points,
                                                          sector_ids, start_distance)
        self.assertEqual(len(distances_1), 3)

        start_distance = 20.
        distances_2 = calculate_2D_intersection_distances(path_0.ecef_path(),
                                                          intersection_points,
                                                          sector_ids, start_distance)
        self.assertEqual(len(distances_2), 3)

    def test_calculate_3D_intersection_distances(self):
        alt_p = ALTITUDE_PROFILE

        distances_1 = calculate_3D_intersection_distances(alt_p, '1', SECTORS['1'],
                                                          0.0, 20 * NM,
                                                          0.0, 4200, True)
        self.assertEqual(len(distances_1), 2)
        self.assertEqual(distances_1[0], 0.0)
        assert_almost_equal(distances_1[-1], 14.16666667 * NM)

        distances_2 = calculate_3D_intersection_distances(alt_p, '2', SECTORS['2'],
                                                          20 * NM, 55 * NM,
                                                          4200, 4200, True)
        self.assertEqual(len(distances_2), 4)
        self.assertEqual(distances_2[0], 20 * NM)
        assert_almost_equal(distances_2[1], 25.83333333 * NM)
        assert_almost_equal(distances_2[2], 49.16666667 * NM)
        self.assertEqual(distances_2[-1], 55 * NM)

        distances_3 = calculate_3D_intersection_distances(alt_p, '3', SECTORS['3'],
                                                          20 * NM, 55 * NM,
                                                          4200, 4200, False)
        self.assertEqual(len(distances_3), 2)
        assert_almost_equal(distances_3[0], 25.83333333 * NM)
        assert_almost_equal(distances_3[-1], 49.16666667 * NM)

    def test_calculate_3D_intersections(self):
        alt_p = ALTITUDE_PROFILE

        sector_ids = ['1', '2', '3', '1']
        distances = [0.0, 20 * NM, 20 * NM, 20 * NM]
        df_2d = pd.DataFrame({'SECTOR_ID': np.array(sector_ids),
                              'DISTANCE': distances})
        df_3d = calculate_3D_intersections(alt_p, SECTORS, df_2d)
        self.assertEqual(df_3d.shape[0], 7)

        ids_3d = df_3d['SECTOR_ID'].values
        distances_3d = df_3d['DISTANCE'].values

        # print(ids_3d)
        # print(distances_3d)

        self.assertEqual(ids_3d[0], '1')
        self.assertEqual(distances_3d[0], 0.0)

        self.assertEqual(ids_3d[-1], '3')
        assert_almost_equal(distances_3d[-1], 49.16666667 * NM)

    def test_calculate_3D_no_intersections(self):

        # Create a altitude profile above the sectors
        HIGH_ALTITUDES = np.array([10000., 11800., 13000.,
                                   13600., 14200., 15400.,
                                   16000., 16000., 16000.,
                                   16000., 15400., 14200.])

        alt_p = AltitudeProfile(DISTANCES, HIGH_ALTITUDES)

        sector_ids = ['1', '2', '3', '1']
        distances = [0.0, 20 * NM, 20 * NM, 20 * NM]
        df_2d = pd.DataFrame({'SECTOR_ID': np.array(sector_ids),
                              'DISTANCE': distances})
        df_3d = calculate_3D_intersections(alt_p, SECTORS, df_2d)
        self.assertEqual(df_3d.shape[0], 0)

    def test_find_3D_airspace_intersections(self):

        path_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)

        timep_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)
        altp_0 = ALTITUDE_PROFILE

        traj_0 = SmoothedTrajectory('123-456-789', path_0, timep_0, altp_0)

        LATS = np.array([0.,  20. / 60.,  40. / 60., 60. / 60.])
        LONS = np.zeros(4, dtype=float)
        sector_ids = ['1', '2', '3', '1']
        points_0 = global_Point3d(LATS, LONS)
        df_3d = find_3D_airspace_intersections(traj_0, path_0.ecef_path(), points_0,
                                               sector_ids, SECTORS)
        self.assertEqual(df_3d.shape[0], 6)

    def test_find_3D_airspace_no_intersections(self):

        path_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)

        timep_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)

        # Create a altitude profile above the sectors
        HIGH_ALTITUDES = np.array([10000., 11800., 13000.,
                                   13600., 14200., 15400.,
                                   16000., 16000., 16000.,
                                   16000., 15400., 14200.])

        alt_p = AltitudeProfile(DISTANCES, HIGH_ALTITUDES)

        traj_0 = SmoothedTrajectory('123-456-789', path_0, timep_0, alt_p)

        LATS = np.array([0.,  20. / 60.,  40. / 60., 60. / 60.])
        LONS = np.zeros(4, dtype=float)
        sector_ids = ['1', '2', '3', '1']
        points_0 = global_Point3d(LATS, LONS)
        df_3d = find_3D_airspace_intersections(traj_0, path_0.ecef_path(), points_0,
                                               sector_ids, SECTORS)
        self.assertEqual(df_3d.shape[0], 0)


if __name__ == '__main__':
    unittest.main()
