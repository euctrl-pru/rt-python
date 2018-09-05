#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from via_sphere import global_Point3d
from pru.trajectory_matching import *


class TestTrajectoryMatching(unittest.TestCase):

    def test_compare_trajectory_positions(self):
        """Test the compare_trajectory_positions function."""
        datetimes_1 = np.arange(np.datetime64('2017-08-01 11:15'),
                                np.datetime64('2017-08-01 11:25'),
                                np.timedelta64(1, 'm'))

        datetimes_2 = np.arange(np.datetime64('2017-08-01 11:20'),
                                np.datetime64('2017-08-01 11:30'),
                                np.timedelta64(1, 'm'))

        datetimes_3 = np.arange(np.datetime64('2017-08-01 11:24'),
                                np.datetime64('2017-08-01 11:34'),
                                np.timedelta64(1, 'm'))

        datetimes_4 = np.arange(np.datetime64('2017-08-01 11:25'),
                                np.datetime64('2017-08-01 11:35'),
                                np.timedelta64(1, 'm'))

        LATITUDES = np.zeros(len(datetimes_1), dtype=float)
        LONGITUDES_1 = np.array([-5 + i for i in range(len(datetimes_1))], dtype=float)
        ecef_points_1 = global_Point3d(LATITUDES, LONGITUDES_1)

        values1 = np.zeros(len(datetimes_1), dtype=float)

        alts1 = np.full(len(datetimes_1), 21000.0, dtype=float)
        alts2 = np.full(len(datetimes_1), 22000.0, dtype=float)

        # Identical trajectories
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                     ecef_points_1, ecef_points_1,
                                                     alts1, alts1))

        # Different altitudes
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts2))

        # Different altitudes, within alt_threshold
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                     ecef_points_1, ecef_points_1,
                                                     alts1, alts2, alt_threshold=1000.0))

        # Second trajectory delayed by 5 mins
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_2,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts1))

        # Second trajectory delayed by 10 mins
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_3,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts1))

        LONGITUDES_2 = np.array([i for i in range(len(datetimes_2))], dtype=float)
        ecef_points_2 = global_Point3d(LATITUDES, LONGITUDES_2)

        # Second trajectory delayed by 5 mins, by first trajectory
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_2,
                                                     ecef_points_1, ecef_points_2,
                                                     alts1, alts1))

        LONGITUDES_3 = np.array([4 + i for i in range(len(datetimes_3))], dtype=float)
        ecef_points_3 = global_Point3d(LATITUDES, LONGITUDES_3)

        # Second trajectory delayed by 9 mins, by end of first trajectory
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_3,
                                                     ecef_points_1, ecef_points_3,
                                                     alts1, alts1))

        # Second trajectory delayed by 10 mins, by end of first trajectory
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                      ecef_points_1, ecef_points_3,
                                                      alts1, alts1))

        # Second trajectory delayed by 10 mins, by end of first trajectory
        # with a minutes time_threshold.
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                     ecef_points_3, ecef_points_1,
                                                     alts1, alts1, time_threshold=60.0,
                                                     speed_threshold=750.0))

        # But other way around, ends are not close enough
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                      ecef_points_1, ecef_points_3,
                                                      alts1, alts1, time_threshold=60.0,
                                                      speed_threshold=750.0))


if __name__ == '__main__':
    unittest.main()
