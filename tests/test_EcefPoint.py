#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.EcefPoint import *

GOLDEN_ANGLE = np.rad2deg(np.arctan(2.0))
LATITUDE = 90.0 - GOLDEN_ANGLE

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

ECEF_ICOSAHEDRON = np.array([[0.0, 0.0, 1.0],
                             [-0.8944271907493363, 0.0, 0.4472135960011169],
                             [-0.276393202421474, -0.8506508080328565, 0.4472135960011169],
                             [0.7236067972396153, -0.5257311123952776, 0.4472135960011169],
                             [0.7236067972396153, 0.5257311123952776, 0.4472135960011169],
                             [-0.276393202421474, 0.8506508080328565, 0.4472135960011169],
                             [-0.7236067972396153, 0.5257311123952776, -0.4472135960011169],
                             [-0.7236067972396153, -0.5257311123952776, -0.4472135960011169],
                             [0.276393202421474, -0.8506508080328565, -0.4472135960011169],
                             [0.8944271907493363, 0.0, -0.4472135960011169],
                             [0.276393202421474, 0.8506508080328565, -0.4472135960011169],
                             [0.0, 0.0, -1.0]])
""" The Icosahedron above in ECEF coordinates. """


class TestEcefPoint(unittest.TestCase):

    def test_EcefPoint_from_lat_long(self):
        """Test conversion of Lat Longs using Icosahedron verticies."""
        for i in range(12):
            lat_long = LAT_LONG_ICOSAHEDRON[i]
            ecef_point = EcefPoint.from_lat_long(lat_long)

            expected_result = ECEF_ICOSAHEDRON[i]
            assert_array_almost_equal(ecef_point.coords, expected_result)

        # Test Latitude above North Pole
        lat_long = [91.0, 0.0]
        ecef_point = EcefPoint.from_lat_long(lat_long)

        expected_result = ECEF_ICOSAHEDRON[0]
        assert_array_almost_equal(ecef_point.coords, expected_result)

        # Test Latitude below South Pole
        lat_long = [-91.0, 0.0]
        ecef_point = EcefPoint.from_lat_long(lat_long)

        expected_result = ECEF_ICOSAHEDRON[11]
        assert_array_almost_equal(ecef_point.coords, expected_result)

    def test_EcefPoint_to_lat_long(self):
        """Test conversion to Lat Longs using Icosahedron verticies."""
        for i in range(12):
            ecef_point = EcefPoint(ECEF_ICOSAHEDRON[i])
            lat_long = ecef_point.to_lat_long()

            expected_result = LAT_LONG_ICOSAHEDRON[i]
            assert_array_almost_equal(lat_long, expected_result)

    def test_hash(self):
        a = EcefPoint(ECEF_ICOSAHEDRON[1])
        b = EcefPoint(ECEF_ICOSAHEDRON[10])
        self.assertTrue(hash(a) == hash(a))
        self.assertTrue(hash(b) == hash(b))
        self.assertFalse(hash(a) == hash(b))
        self.assertFalse(hash(b) == hash(a))

    def test_repr(self):
        a = EcefPoint(ECEF_ICOSAHEDRON[1])
        self.assertEqual('EcefPoint([-0.89442719  0.          0.4472136 ])',
                         repr(a))
        b = EcefPoint(ECEF_ICOSAHEDRON[10])
        self.assertEqual('EcefPoint([ 0.2763932   0.85065081 -0.4472136 ])',
                         repr(b))

    def test_str(self):
        a = EcefPoint(ECEF_ICOSAHEDRON[1])
        self.assertEqual('EcefPoint(26.565051209181547, 180.0)', str(a))
        b = EcefPoint(ECEF_ICOSAHEDRON[10])
        self.assertEqual('EcefPoint(-26.565051209181547, 71.999999983236208)',
                         str(b))

    def test_eq(self):
        a = EcefPoint(ECEF_ICOSAHEDRON[1])
        b = EcefPoint(ECEF_ICOSAHEDRON[10])

        self.assertTrue(a == a)
        self.assertTrue(b == b)
        self.assertFalse(a == b)
        self.assertFalse(b == a)

    def test_norm(self):
        for i in range(12):
            ecef_point = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(ecef_point.norm(), 1.0)

    def test_abs(self):
        for i in range(12):
            ecef_point = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(abs(ecef_point), 1.0)

    def test_normalize(self):
        for i in range(12):
            ecef_point = 2.0 * EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(abs(ecef_point), 2.0)
            self.assertTrue(ecef_point)

            ecef_point.normalize()
            assert_almost_equal(abs(ecef_point), 1.0)
            self.assertTrue(ecef_point)

        ecef_point = EcefPoint([EPSILON, -EPSILON, EPSILON])
        assert_almost_equal(abs(ecef_point), 0.0)
        self.assertTrue(ecef_point)

        ecef_point.normalize()
        assert_almost_equal(abs(ecef_point), 0.0)
        self.assertFalse(ecef_point)

    def test_neg_and_pos(self):
        ecef_point = EcefPoint(ECEF_ICOSAHEDRON[0])
        self.assertTrue(+ecef_point == ecef_point)
        self.assertTrue(-ecef_point == EcefPoint(ECEF_ICOSAHEDRON[11]))

        self.assertFalse(-ecef_point == ecef_point)
        self.assertFalse(+ecef_point == EcefPoint(ECEF_ICOSAHEDRON[11]))

    def test_add_and_sub(self):
        ecef_point1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point2 = EcefPoint(ECEF_ICOSAHEDRON[2])

        ecef_point_3 = ecef_point1 + ecef_point2
        assert_almost_equal(abs(ecef_point_3), 1.7013016170169837)

        ecef_point_4 = ecef_point_3 - ecef_point2
        assert_almost_equal(abs(ecef_point_4), 1.0)
        self.assertTrue(ecef_point_4 == ecef_point1)

        ecef_point_5 = ecef_point_3 - ecef_point1
        assert_almost_equal(abs(ecef_point_5), 1.0)
        self.assertTrue(ecef_point_5 == ecef_point2)

    def test_mul(self):
        ecef_point1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        non_scalar = 'hello'

        try:
            ecef_point1 * non_scalar
        except TypeError:
            self.assertTrue(1)
        else:
            self.assertTrue(0)

    def test_getitem(self):
        a = EcefPoint(ECEF_ICOSAHEDRON[10])
        assert_almost_equal(a[0], 0.276393202421474)
        assert_almost_equal(a[1], 0.8506508080328565)
        assert_almost_equal(a[2], -0.4472135960011169)

        try:
            a[1.0]
        except TypeError:
            self.assertTrue(1)
        else:
            self.assertTrue(0)

    def test_distance_radians(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        self.assertEqual(distance_radians(ecef_point_0, ecef_point_0), 0.0)

        result_1 = np.arctan(2.0)
        for i in range(1, 6):
            ecef_point_i = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(distance_radians(ecef_point_0, ecef_point_i),
                                result_1)

        result_2 = np.pi - result_1  # 2.0344439363560154
        for i in range(6, 11):
            ecef_point_i = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(distance_radians(ecef_point_0, ecef_point_i),
                                result_2)

        ecef_point_11 = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(distance_radians(ecef_point_0, ecef_point_11),
                            np.pi)

    def test_distance_nm(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        self.assertEqual(distance_radians(ecef_point_0, ecef_point_0), 0.0)

        result_1 = 60.0 * np.rad2deg(np.arctan(2.0))
        for i in range(1, 6):
            ecef_point_i = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(distance_nm(ecef_point_0, ecef_point_i),
                                result_1, decimal=5)

        result_2 = 60.0 * 180.0 - result_1
        for i in range(6, 11):
            ecef_point_i = EcefPoint(ECEF_ICOSAHEDRON[i])
            assert_almost_equal(distance_nm(ecef_point_0, ecef_point_i),
                                result_2, decimal=5)

        ecef_point_11 = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(distance_nm(ecef_point_0, ecef_point_11),
                            180.0 * 60.0)


if __name__ == '__main__':
    unittest.main()
