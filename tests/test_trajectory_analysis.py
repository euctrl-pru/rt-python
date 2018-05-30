#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from os import environ as env
from pru.trajectory_analysis import *

TEST_DATA_HOME = 'TEST_DATA_HOME'

NM = np.deg2rad(1.0 / 60.0)

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 5400.,
                      6000., 6000., 6000.,
                      6000., 5400., 4200.])

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

DISTANCES = np.array([0., 27.171707 * NM, 76.922726 * NM,
                      224.561621 * NM, 226.056657 * NM, 227.510208 * NM,
                      228.901381 * NM, 230.240527 * NM, 231.299789 * NM,
                      232.358631 * NM, 233.438427 * NM, 233.645865 * NM])

TEST_ALTITUDES = np.array([35200, 35200,  35200,
                           34800, 34800,  34800,
                           35200, 35300,  35200,
                           35000, 35000,  35000])


class TestTrajectorySmoothing(unittest.TestCase):

    def test_calculate_cruise_delta_alts(self):

        cruise_delta_alts = [200.0, 200.0, -200.0, -200.0, 0.0]

        cruise_indicies = find_cruise_sections(TEST_ALTITUDES)
        results = calculate_cruise_delta_alts(TEST_ALTITUDES, cruise_indicies)
        assert_array_almost_equal(results, cruise_delta_alts)

    def test_analyse_altitudes(self):

        cruise_indicies = find_cruise_sections(ALTITUDES)

        altp, alt_sd, max_alt = analyse_altitudes(DISTANCES, ALTITUDES, cruise_indicies)

        self.assertEqual(len(altp.altitudes), len(ALTITUDES) - 2)

    def test_analyse_trajectory_1(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/clean_cpr_259599_BAW307_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME'])

        flight_id = '259599'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[1], int(AltitudeProfileType.CLIMBING_AND_DESCENDING))
        self.assertEqual(metrics[3], 0)
        # print(metrics)

    def test_analyse_trajectory_2(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/clean_cpr_255332_SAS1643_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME'])

        flight_id = '255332'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[1], int(AltitudeProfileType.CLIMBING_AND_DESCENDING))
        self.assertEqual(metrics[3], 1)
        # print(metrics)

    def test_analyse_trajectory_3(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/295765_cpr_positions_2017-07-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME'])

        flight_id = '295765'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[1], int(AltitudeProfileType.CLIMBING))
        self.assertEqual(metrics[3], 1)

    def test_analyse_trajectory_4(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/286375_cpr_positions_2017-07-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME'])

        flight_id = '286375'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[1], int(AltitudeProfileType.CLIMBING))
        self.assertEqual(metrics[3], 1)


if __name__ == '__main__':
    unittest.main()
