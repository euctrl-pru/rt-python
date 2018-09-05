#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import pandas as pd
from numpy.testing import assert_almost_equal
from via_sphere import global_Point3d, distance_radians
from pru.sphere_functions import calculate_position, find_index_and_ratio

GOLDEN_ANGLE = np.arctan(2.0)
LATITUDE = 90.0 - np.rad2deg(GOLDEN_ANGLE)
NM = np.deg2rad(1.0 / 60.0)

LAT_LONG_ICOSAHEDRON = np.array([[90.0, 0.0],
                                 [LATITUDE, 180.0],
                                 [LATITUDE, -1.5 * 72.0],
                                 [LATITUDE, -0.5 * 72.0],
                                 [LATITUDE, 0.5 * 72.0],
                                 [LATITUDE, 1.5 * 72.0],
                                 [-LATITUDE, 2.0 * 72.0],
                                 [-LATITUDE, -2.0 * 72.0],
                                 [-LATITUDE, -1.0 * 72.0],
                                 [-LATITUDE, 0.0],
                                 [-LATITUDE, 1.0 * 72.0],
                                 [-90.0, 0.0]])
""" An Icosahedron with vertices at the North and South poles. """

PANDAS_ICOSAHEDRON = pd.DataFrame(LAT_LONG_ICOSAHEDRON, columns=['LAT', 'LON'])


class TestSphereFunctions(unittest.TestCase):

    def test_calculate_position(self):
        ecef_points = global_Point3d(PANDAS_ICOSAHEDRON['LAT'],
                                     PANDAS_ICOSAHEDRON['LON'])

        point_0 = calculate_position(ecef_points, 0)
        assert_almost_equal(distance_radians(point_0, ecef_points[0]), 0.0)

        point_11 = calculate_position(ecef_points, 11)
        assert_almost_equal(distance_radians(point_11, ecef_points[-1]), 0.0)

        point_11_5 = calculate_position(ecef_points, 11, ratio=0.5)
        assert_almost_equal(distance_radians(point_11_5, ecef_points[-1]), 0.0)

        point_5_5 = calculate_position(ecef_points, 5, ratio=0.5)
        assert_almost_equal(distance_radians(point_5_5, ecef_points[5]),
                            0.5 * GOLDEN_ANGLE)
        assert_almost_equal(distance_radians(point_5_5, ecef_points[6]),
                            0.5 * GOLDEN_ANGLE)

        point_7_25 = calculate_position(ecef_points, 7, ratio=0.25)
        assert_almost_equal(distance_radians(point_7_25, ecef_points[7]),
                            0.25 * GOLDEN_ANGLE)
        assert_almost_equal(distance_radians(point_7_25, ecef_points[8]),
                            0.75 * GOLDEN_ANGLE)

    def test_find_index_and_ratio(self):
        ecef_points = global_Point3d(PANDAS_ICOSAHEDRON['LAT'],
                                     PANDAS_ICOSAHEDRON['LON'])

        point0 = ecef_points[0]
        index0, ratio0 = find_index_and_ratio(ecef_points, point0)
        self.assertEqual(index0, 0)
        assert_almost_equal(ratio0, 0.0)

        point0_5 = calculate_position(ecef_points, 0, 0.5)
        index0_5, ratio0_5 = find_index_and_ratio(ecef_points, point0_5)
        self.assertEqual(index0_5, 0)
        assert_almost_equal(ratio0_5, 0.5)

        point0_99 = calculate_position(ecef_points, 0, 0.99)
        index0_99, ratio0_99 = find_index_and_ratio(ecef_points, point0_99)
        self.assertEqual(index0_99, 0)
        assert_almost_equal(ratio0_99, 0.99)

        point1 = ecef_points[1]
        index1, ratio1 = find_index_and_ratio(ecef_points, point1)
        self.assertEqual(index1, 1)
        assert_almost_equal(ratio1, 0.0)

        point1_01 = calculate_position(ecef_points, 1, 0.01)
        index1_01, ratio1_01 = find_index_and_ratio(ecef_points, point1_01)
        self.assertEqual(index1_01, 1)
        assert_almost_equal(ratio1_01, 0.01)

        point5 = calculate_position(ecef_points, 5)
        index5, ratio5 = find_index_and_ratio(ecef_points, point5)
        self.assertEqual(index5, 5)
        assert_almost_equal(ratio5, 0.0)

        point7_5 = calculate_position(ecef_points, 7, 0.5)
        index7_5, ratio7_5 = find_index_and_ratio(ecef_points, point7_5)
        self.assertEqual(index7_5, 7)
        assert_almost_equal(ratio7_5, 0.5)

        point10_99 = calculate_position(ecef_points, 10, 0.99)
        index10_99, ratio10_99 = find_index_and_ratio(ecef_points, point10_99)
        self.assertEqual(index10_99, 10)
        assert_almost_equal(ratio10_99, 0.99)

        point11 = ecef_points[11]
        index11, ratio11 = find_index_and_ratio(ecef_points, point11)
        self.assertEqual(index11, 11)
        assert_almost_equal(ratio11, 0.0)


if __name__ == '__main__':
    unittest.main()
