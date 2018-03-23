#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_array_almost_equal
from pru.AltitudeProfile import AltitudeProfile, find_level_sections

NM = np.deg2rad(1.0 / 60.0)

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 5400.,
                      6000., 6000., 6000.,
                      6000., 5400., 4200.])
DISTANCES = np.array([0., 5 * NM, 10 * NM,
                      15 * NM, 20 * NM, 25 * NM,
                      30 * NM, 35 * NM, 40 * NM,
                      45 * NM, 50 * NM, 55 * NM])


class TestAltitudeProfile(unittest.TestCase):

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
