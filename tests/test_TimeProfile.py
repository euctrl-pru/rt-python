#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.TimeProfile import TimeProfile

NM = np.deg2rad(1.0 / 60.0)

START_TIME = np.datetime64('2017-08-01T08:47:31.000')

ELAPSED_TIMES = np.array([0.,   292.,   718.,
                          2543.,  2573.,  2603.,
                          2633.,  2663.,  2693.,
                          2723.,  2753.,  2759.])

DISTANCES = np.array([0., 27.171707 * NM, 76.922726 * NM,
                      224.561621 * NM, 226.056657 * NM, 227.510208 * NM,
                      228.901381 * NM, 230.240527 * NM, 231.299789 * NM,
                      232.358631 * NM, 233.438427 * NM, 233.645865 * NM])


class TestTimeProfile(unittest.TestCase):

    def test_TimeProfile_interpolate_by_distance(self):
        profile_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)

        distances_0 = np.array([0., 2 * NM, 8 * NM, DISTANCES[2]])
        times_0 = profile_0.interpolate_by_distance(distances_0)
        self.assertEqual(len(times_0), len(distances_0))
        self.assertEqual(times_0[0], ELAPSED_TIMES[0])
        self.assertEqual(times_0[-1], ELAPSED_TIMES[2])

    def test_TimeProfile_interpolate_by_elapsed_time(self):
        profile_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)

        times_0 = np.array([0.0, 292.0, 500.0, 718.0])
        distances_0 = profile_0.interpolate_by_elapsed_time(times_0)
        self.assertEqual(len(distances_0), len(times_0))
        self.assertEqual(distances_0[0], DISTANCES[0])
        assert_almost_equal(distances_0[2], 51.053368441692193 * NM)
        self.assertEqual(distances_0[-1], DISTANCES[2])

    def test_TimeProfile_calculate_average_period(self):

        profile_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)

        period_0 = profile_0.calculate_average_period(75. * NM, 75. * NM)
        self.assertEqual(period_0, 0.0)
        period_1 = profile_0.calculate_average_period(0.0, 75. * NM)
        self.assertEqual(period_1, 0.0)
        period_2 = profile_0.calculate_average_period(0.0, 225. * NM)
        assert_almost_equal(period_2, 1125.5)
        period_3 = profile_0.calculate_average_period(225. * NM, 233.645865 * NM)
        assert_almost_equal(period_3, 26.571428571428573)
        period_4 = profile_0.calculate_average_period(225. * NM, 235.0 * NM)
        assert_almost_equal(period_4, 26.571428571428573)

    def test_TimeProfile_json(self):

        profile_0 = TimeProfile(START_TIME, DISTANCES, ELAPSED_TIMES)
        s = profile_0.dumps()
        # print(s)

        json_1 = json.loads(s)
        profile_1 = TimeProfile.loads(json_1)

        self.assertEqual(profile_1.start_time, START_TIME)
        assert_array_almost_equal(profile_1.distances, profile_0.distances)
        assert_array_almost_equal(profile_1.elapsed_times, profile_0.elapsed_times)


if __name__ == '__main__':
    unittest.main()
