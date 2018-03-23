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


class TestTrajectorySmoothing(unittest.TestCase):

    def test_closest_cruising_altitude(self):
        self.assertEqual(closest_cruising_altitude(35000), 35000)
        self.assertEqual(closest_cruising_altitude(34500), 35000)
        self.assertEqual(closest_cruising_altitude(35400), 35000)

    def test_is_cruising(self):
        self.assertTrue(is_cruising(35000, 35000))
        self.assertTrue(is_cruising(35000))
        self.assertTrue(is_cruising(34800))
        self.assertTrue(is_cruising(35200))

        self.assertFalse(is_cruising(34799))
        self.assertFalse(is_cruising(35201))

        self.assertFalse(is_cruising(35000, 36000))

    def test_in_cruise_level_range(self):
        CRUISE_ALTITUDES = np.array([35200, 35100,  35000,
                                     34900, 34800,  34800])
        self.assertTrue(in_cruise_level_range(CRUISE_ALTITUDES, 35000))

        NON_CRUISE_ALTITUDES = np.array([35200, 35100,  35000,
                                         34900, 34700,  34800])
        self.assertFalse(in_cruise_level_range(NON_CRUISE_ALTITUDES, 35000))

    def test_find_cruise_sections(self):
        TEST_ALTITUDES = np.array([35200, 35200,  35200,
                                   34800, 34800,  34800,
                                   35200, 35300,  35200,
                                   35000, 35000,  35000])

        indicies = find_cruise_sections(TEST_ALTITUDES)
        self.assertEqual(len(indicies), 4)
        self.assertEqual(indicies[0], 0)
        self.assertEqual(indicies[1], 5)
        self.assertEqual(indicies[2], 9)
        self.assertEqual(indicies[3], 11)

    def test_classify_altitude_profile(self):
        CRUISE_ALTITUDES = np.array([35000, 35000,  35000,
                                     35000, 35000,  35000])
        cruise_indicies = find_cruise_sections(CRUISE_ALTITUDES)
        self.assertEqual(classify_altitude_profile(CRUISE_ALTITUDES, cruise_indicies),
                         AltitudeProfileType.CRUISING)

        CLIMB_ALTITUDES = np.array([34000, 34500,  35000,
                                    35000, 35500,  36000])
        climb_indicies = find_cruise_sections(CLIMB_ALTITUDES)
        self.assertEqual(classify_altitude_profile(CLIMB_ALTITUDES, climb_indicies),
                         AltitudeProfileType.CLIMBING)

        DESCENT_ALTITUDES = np.array([36000, 35500,  35000,
                                      35000, 34500,  34000])
        descent_indicies = find_cruise_sections(DESCENT_ALTITUDES)
        self.assertEqual(classify_altitude_profile(DESCENT_ALTITUDES, descent_indicies),
                         AltitudeProfileType.DESCENDING)

        indicies = find_cruise_sections(ALTITUDES)
        self.assertEqual(classify_altitude_profile(ALTITUDES, indicies),
                         AltitudeProfileType.CLIMBING_AND_DESCENDING)

    def test_analyse_altitudes(self):

        cruise_indicies = find_cruise_sections(ALTITUDES)

        altp, alt_error = analyse_altitudes(DISTANCES, ALTITUDES, cruise_indicies)

        self.assertEqual(len(altp.altitudes), len(ALTITUDES) - 2)

    def test_analyse_trajectory_1(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/clean_cpr_259599_BAW307_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME_SOURCE'])

        flight_id = '259599'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[2], 0)
        self.assertEqual(metrics[3], int(AltitudeProfileType.CLIMBING_AND_DESCENDING))
        # print(metrics)

    def test_analyse_trajectory_2(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        filename = '/clean_cpr_255332_SAS1643_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename,
                                parse_dates=['TIME_SOURCE'])

        flight_id = '255332'
        across_track_tolerance = 0.25
        traj, metrics = analyse_trajectory(flight_id, points_df,
                                           across_track_tolerance)
        self.assertEqual(metrics[0], flight_id)
        self.assertEqual(metrics[2], 1)
        self.assertEqual(metrics[3], int(AltitudeProfileType.CLIMBING_AND_DESCENDING))
        # print(metrics)


if __name__ == '__main__':
    unittest.main()
