#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from os import environ as env
from pru.EcefPoint import rad2nm
from pru.EcefPath import PointType
from pru.TimeProfile import TimeProfile
from pru.AltitudeProfile import AltitudeProfile
from pru.trajectory_analysis import analyse_trajectory
from pru.trajectory_interpolation import *

TEST_DATA_HOME = 'TEST_DATA_HOME'

NM = np.deg2rad(1.0 / 60.0)

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 5400.,
                      6000., 6000., 6000.,
                      6000., 5400., 4800.])

TIMES = np.array([np.datetime64('2017-08-01T08:47:31.000'),
                  np.datetime64('2017-08-01T08:52:23.000'),
                  np.datetime64('2017-08-01T08:59:29.000'),

                  np.datetime64('2017-08-01T09:29:54.000'),
                  np.datetime64('2017-08-01T09:30:24.000'),
                  np.datetime64('2017-08-01T09:30:54.000'),

                  np.datetime64('2017-08-01T09:31:24.000'),
                  np.datetime64('2017-08-01T09:31:54.000'),
                  np.datetime64('2017-08-01T09:32:24.000'),

                  np.datetime64('2017-08-01T09:32:54.000'),
                  np.datetime64('2017-08-01T09:33:24.000'),
                  np.datetime64('2017-08-01T09:33:30.000')])

ELAPSED_TIMES = np.array([0.0, 292.0, 718.0,
                          2543.0, 2573.0, 2603.0,
                          2633.0, 2663.0, 2693.0,
                          2723.0, 2753.0, 2759.0])

DISTANCES = np.array([0., 27.171707 * NM, 76.922726 * NM,
                      224.561621 * NM, 226.056657 * NM, 227.510208 * NM,
                      228.901381 * NM, 230.240527 * NM, 231.299789 * NM,
                      232.358631 * NM, 233.438427 * NM, 233.645865 * NM])


class TestTrajectoryInterpolation(unittest.TestCase):

    def test_interpolate_altitude_profile(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        distances_0 = np.array([0., 20.0 * NM, 50.0 * NM, DISTANCES[2]])
        alts_0 = interpolate_altitude_profile(profile, distances_0)
        self.assertEqual(len(alts_0), len(distances_0))
        self.assertEqual(alts_0[0], ALTITUDES[0])
        self.assertEqual(alts_0[-1], ALTITUDES[2])

    def test_interpolate_time_profile_by_distance(self):
        profile = TimeProfile(TIMES[0], DISTANCES, ELAPSED_TIMES)

        distances_0 = np.array([0., 2 * NM, 8 * NM, DISTANCES[2]])
        times_0 = interpolate_time_profile_by_distance(profile, distances_0)
        self.assertEqual(len(times_0), len(distances_0))
        self.assertEqual(times_0[0], ELAPSED_TIMES[0])
        self.assertEqual(times_0[-1], ELAPSED_TIMES[2])

    def test_interpolate_time_profile_by_elapsed_time(self):
        profile = TimeProfile(TIMES[0], DISTANCES, ELAPSED_TIMES)

        times_0 = np.array([0.0, 292.0, 500.0, 718.0])
        distances_0 = interpolate_time_profile_by_elapsed_time(profile, times_0)
        self.assertEqual(len(distances_0), len(times_0))
        self.assertEqual(distances_0[0], DISTANCES[0])
        assert_almost_equal(distances_0[2], 51.053368441692193 * NM)
        self.assertEqual(distances_0[-1], DISTANCES[2])

    def test_calculate_interpolation_times(self):

        POINT_TYPES = [PointType.Waypoint, PointType.Waypoint, PointType.Waypoint,
                       PointType.Waypoint, PointType.Waypoint, PointType.Waypoint,
                       PointType.Waypoint, PointType.Waypoint, PointType.Waypoint,
                       PointType.Waypoint, PointType.Waypoint, PointType.Waypoint]

        times_0 = calculate_interpolation_times(ELAPSED_TIMES, POINT_TYPES,
                                                6.0, 1.0)
        self.assertEqual(len(times_0), 470)
        self.assertEqual(times_0[0], ELAPSED_TIMES[0])
        self.assertEqual(times_0[-1], ELAPSED_TIMES[-1])

        # increase straight period
        times_1 = calculate_interpolation_times(ELAPSED_TIMES, POINT_TYPES,
                                                12.0, 1.0)
        self.assertEqual(len(times_1), 237)
        self.assertEqual(times_1[0], ELAPSED_TIMES[0])
        self.assertEqual(times_1[-1], ELAPSED_TIMES[-1])

        # Add a Turn
        POINT_TYPES[3] = PointType.TurnStart
        POINT_TYPES[4] = PointType.TurnFinish
        times_2 = calculate_interpolation_times(ELAPSED_TIMES, POINT_TYPES,
                                                6.0, 1.0)
        self.assertEqual(len(times_2), 495)
        self.assertEqual(times_2[0], ELAPSED_TIMES[0])
        self.assertEqual(times_2[-1], ELAPSED_TIMES[-1])

        # Add a another Turn
        POINT_TYPES[7] = PointType.TurnStart
        POINT_TYPES[8] = PointType.TurnFinish
        times_3 = calculate_interpolation_times(ELAPSED_TIMES, POINT_TYPES,
                                                6.0, 1.0)
        self.assertEqual(len(times_3), 520)
        self.assertEqual(times_3[0], ELAPSED_TIMES[0])
        self.assertEqual(times_3[-1], ELAPSED_TIMES[-1])

    def test_calculate_speeds(self):

        speeds = calculate_speeds(ELAPSED_TIMES, rad2nm(DISTANCES))
        self.assertEqual(len(speeds), len(ELAPSED_TIMES))
        assert_almost_equal(speeds[0], 334.99364794520545)
        assert_almost_equal(speeds[-1], 124.46279999998069)

    def test_calculate_vertical_speeds(self):

        vertical_speeds = calculate_vertical_speeds(ELAPSED_TIMES, ALTITUDES)
        self.assertEqual(len(vertical_speeds), len(ELAPSED_TIMES))
        assert_almost_equal(vertical_speeds[0], 369.86301369863014)
        assert_almost_equal(vertical_speeds[-1], -6000.0)

    def test_convert_ground_tracks(self):

        ANGLES_RADS = np.array([0., np.pi, 2.0 * np.pi,
                                -np.pi, -0.5 * np.pi, -2.0 * np.pi])

        TRACKS_DEGS = np.array([0., 180., 360.0,
                                180.0, 270.0, 0.0])

        results = convert_ground_tracks(ANGLES_RADS)
        assert_array_almost_equal(results, TRACKS_DEGS)

    def test_interpolate_trajectory_positions(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/clean_cpr_255332_SAS1643_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME_SOURCE'])

        flight_id = '123-456-7890'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)

        output_df = interpolate_trajectory_positions(traj, DEFAULT_STRAIGHT_INTERVAL,
                                                     DEFAULT_TURN_INTERVAL)
        self.assertEqual(len(output_df), 1314)


if __name__ == '__main__':
    unittest.main()
