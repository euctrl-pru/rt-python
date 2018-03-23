#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_array_almost_equal
from pru.HorizontalPath import HorizontalPath

GOLDEN_ANGLE = np.rad2deg(np.arctan(2.0))
LATITUDE = 90.0 - GOLDEN_ANGLE

NM = np.deg2rad(1.0 / 60.0)

ROUTE_LATS = np.array([90.0, LATITUDE, LATITUDE,
                       LATITUDE, LATITUDE, LATITUDE,
                       -LATITUDE, -LATITUDE, -LATITUDE,
                       -LATITUDE, -LATITUDE, -90.0])
ROUTE_LONS = np.array([0.0, 180.0, -1.5 * 72.0,
                       -0.5 * 72.0, 0.5 * 72.0, 1.5 * 72.0,
                       2.0 * 72.0, -2.0 * 72.0, -1.0 * 72.0,
                       0.0, 1.0 * 72.0, 0.0])
""" An Icosahedron with vertices at the North and South poles. """

TURN_DISTANCES = np.array([0., 0., 10 * NM,
                           20 * NM, 20 * NM, 20 * NM,
                           20 * NM, 20 * NM, 20 * NM,
                           20 * NM, 0., 0.])


class TestHorizontalPath(unittest.TestCase):

    def test_HorizontalPath(self):
        traj_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)
        s = traj_0.dumps()

        # print(s)

        json_1 = json.loads(s)
        traj_1 = HorizontalPath.loads(json_1)

        assert_array_almost_equal(traj_1.lats, traj_0.lats)
        assert_array_almost_equal(traj_1.lons, traj_0.lons)
        assert_array_almost_equal(traj_1.tids, traj_0.tids)


if __name__ == '__main__':
    unittest.main()
