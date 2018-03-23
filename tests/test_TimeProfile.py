#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_array_almost_equal
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
