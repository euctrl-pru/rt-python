#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.AltitudeProfile import *

NM = np.deg2rad(1.0 / 60.0)

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 5400.,
                      6000., 6000., 6000.,
                      6000., 5400., 4200.])

DISTANCES = np.array([0., 5 * NM, 10 * NM,
                      15 * NM, 20 * NM, 25 * NM,
                      30 * NM, 35 * NM, 40 * NM,
                      45 * NM, 50 * NM, 55 * NM])

TEST_ALTITUDES = np.array([35200, 35200,  35200,
                           34800, 34800,  34800,
                           35200, 35300,  35200,
                           35000, 35000,  35000])


class TestAltitudeProfile(unittest.TestCase):

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

    def test_find_level_sections(self):
        cruise_indicies = find_level_sections(ALTITUDES)
        self.assertEqual(len(cruise_indicies), 2)
        self.assertEqual(cruise_indicies[0], 6)
        self.assertEqual(cruise_indicies[-1], 9)

        level_indicies = find_level_sections(ALTITUDES[6: 10])
        self.assertEqual(len(level_indicies), 2)
        self.assertEqual(level_indicies[0], 0)
        self.assertEqual(level_indicies[-1], 3)

        climb_indicies = find_level_sections(ALTITUDES[0: 6])
        self.assertEqual(len(climb_indicies), 0)

        descent_indicies = find_level_sections(ALTITUDES[9:])
        self.assertEqual(len(descent_indicies), 0)

    def test_find_cruise_sections(self):

        indicies = find_cruise_sections(TEST_ALTITUDES)
        self.assertEqual(len(indicies), 4)
        self.assertEqual(indicies[0], 0)
        self.assertEqual(indicies[1], 5)
        self.assertEqual(indicies[2], 9)
        self.assertEqual(indicies[3], 11)

        NON_CRUISING_ALTITUDES = np.array([30000, 30000,  30000,
                                           31500, 32500,  32500,
                                           33000, 33000,  33000,
                                           32500, 32000,  32000])
        indicies_2 = find_cruise_sections(NON_CRUISING_ALTITUDES)
        self.assertEqual(len(indicies_2), 6)
        self.assertEqual(indicies_2[0], 0)
        self.assertEqual(indicies_2[1], 2)
        self.assertEqual(indicies_2[2], 6)
        self.assertEqual(indicies_2[3], 8)
        self.assertEqual(indicies_2[4], 10)
        self.assertEqual(indicies_2[5], 11)

    def test_find_cruise_positions(self):

        cruise_positions = [False, True, True,
                            True, True, False,
                            False, False, False,
                            False, True, False]

        cruise_indicies = find_cruise_sections(TEST_ALTITUDES)
        results = find_cruise_positions(len(TEST_ALTITUDES), cruise_indicies)
        assert_array_almost_equal(results, cruise_positions)

        NON_CRUISING_ALTITUDES = np.array([30000, 30000,  30000,
                                           31500, 32500,  32500,
                                           33000, 33000,  33000,
                                           32500, 32000,  32000])
        cruise_positions_2 = [False, True, False,
                              False, False, False,
                              False, True, False,
                              False, False, False]

        cruise_indicies_2 = find_cruise_sections(NON_CRUISING_ALTITUDES)
        results_2 = find_cruise_positions(len(NON_CRUISING_ALTITUDES), cruise_indicies_2)
        assert_array_almost_equal(results_2, cruise_positions_2)

    def test_set_cruise_altitudes(self):

        CRUISE_SET_ALTITUDES = np.array([34800, 34900,  34900,
                                         34900, 34900,  34800])

        cruise_indicies = find_cruise_sections(CRUISE_SET_ALTITUDES)
        altitudes = set_cruise_altitudes(CRUISE_SET_ALTITUDES, cruise_indicies)
        self.assertEqual(altitudes[1], 35000)
        self.assertEqual(altitudes[4], 35000)

    def test_classify_altitude_profile(self):
        CRUISE_ALTITUDES = np.array([35000, 35000,  35000,
                                     35000, 35000,  35000])
        self.assertEqual(classify_altitude_profile(CRUISE_ALTITUDES),
                         AltitudeProfileType.CRUISING)

        CLIMB_ALTITUDES = np.array([34000, 34500,  35000,
                                    35000, 35500,  36000])
        self.assertEqual(classify_altitude_profile(CLIMB_ALTITUDES),
                         AltitudeProfileType.CLIMBING)

        DESCENT_ALTITUDES = np.array([36000, 35500,  35000,
                                      35000, 34500,  34000])
        self.assertEqual(classify_altitude_profile(DESCENT_ALTITUDES),
                         AltitudeProfileType.DESCENDING)

        self.assertEqual(classify_altitude_profile(ALTITUDES),
                         AltitudeProfileType.CLIMBING_AND_DESCENDING)

    def test_AltitudeProfile_profile_type(self):
        CRUISE_ALTITUDES = np.array([35000, 35000,  35000,
                                     35000, 35000,  35000])
        profile_1 = AltitudeProfile(DISTANCES[:6], CRUISE_ALTITUDES)
        self.assertEqual(profile_1.type(), AltitudeProfileType.CRUISING)

        CLIMB_ALTITUDES = np.array([34000, 34500,  35000,
                                    35000, 35500,  36000])
        profile_2 = AltitudeProfile(DISTANCES[:6], CLIMB_ALTITUDES)
        self.assertEqual(profile_2.type(), AltitudeProfileType.CLIMBING)

        DESCENT_ALTITUDES = np.array([36000, 35500,  35000,
                                      35000, 34500,  34000])
        profile_3 = AltitudeProfile(DISTANCES[:6], DESCENT_ALTITUDES)
        self.assertEqual(profile_3.type(), AltitudeProfileType.DESCENDING)

        profile = AltitudeProfile(DISTANCES, ALTITUDES)
        self.assertEqual(profile.type(), AltitudeProfileType.CLIMBING_AND_DESCENDING)

    def test_AltitudeProfile_interpolate(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        distances_0 = np.array([0., 20.0 * NM, 50.0 * NM, DISTANCES[2]])
        alts_0 = profile.interpolate(distances_0)
        self.assertEqual(len(alts_0), len(distances_0))
        self.assertEqual(alts_0[0], ALTITUDES[0])
        self.assertEqual(alts_0[-1], ALTITUDES[2])

    def test_AltitudeProfile_altitude_range(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        min_alt_0, max_alt_0 = profile.altitude_range(0.0, 22.5 * NM)
        self.assertEqual(min_alt_0, 0.0)
        assert_almost_equal(max_alt_0, 4800.0)

        min_alt_1, max_alt_1 = profile.altitude_range(22.5 * NM, 52.5 * NM)
        assert_almost_equal(min_alt_1, 4800.0)
        assert_almost_equal(max_alt_1, 6000.0)

        min_alt_2, max_alt_2 = profile.altitude_range(52.5 * NM, 56.0 * NM)
        assert_almost_equal(min_alt_2, 4200.0)
        assert_almost_equal(max_alt_2, 4800.0)

    def test_AltitudeProfile_top_of_climb_index(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        self.assertEqual(profile.top_of_climb_index(), 6)

    def test_AltitudeProfile_top_of_descent_index(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        self.assertEqual(profile.top_of_descent_index(), 7)

    def test_AltitudeProfile_top_of_climb_distance(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        self.assertEqual(profile.top_of_climb_distance(), DISTANCES[6])

    def test_AltitudeProfile_top_of_descent_distancex(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        self.assertEqual(profile.top_of_descent_distance(), DISTANCES[7])

    def test_AltitudeProfile_intersection_distances(self):
        profile = AltitudeProfile(DISTANCES, ALTITUDES)

        # There should be no intersection at max latitude
        distances_0 = profile.intersection_distances(6000.0, 0.0, 56.0 * NM)
        self.assertEqual(len(distances_0), 0)

        distances_1 = profile.intersection_distances(4800.0, 17.5 * NM, 25.5 * NM)
        self.assertEqual(len(distances_1), 1)
        assert_almost_equal(distances_1[0], 22.5 * NM)

        distances_2 = profile.intersection_distances(4800.0, 25.0 * NM, 53.0 * NM)
        self.assertEqual(len(distances_2), 1)
        assert_almost_equal(distances_2[0], 52.5 * NM)

        distances_3 = profile.intersection_distances(4800.0, 0.0, 56.0 * NM)
        self.assertEqual(len(distances_3), 2)
        assert_almost_equal(distances_3[0], 22.5 * NM)
        assert_almost_equal(distances_3[-1], 52.5 * NM)

    def test_AltitudeProfile_json(self):
        profile_0 = AltitudeProfile(DISTANCES, ALTITUDES)
        s = profile_0.dumps()

        # print(s)

        json_1 = json.loads(s)
        profile_1 = AltitudeProfile.loads(json_1)

        assert_array_almost_equal(profile_1.distances, profile_0.distances)
        assert_array_almost_equal(profile_1.altitudes, profile_0.altitudes)


if __name__ == '__main__':
    unittest.main()
