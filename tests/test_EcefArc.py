#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.EcefArc import *
from pru.EcefPoint import *

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
""" An ECEF Icosahedron with vertices at the North and South poles. """


class TestEcefArc(unittest.TestCase):

    def test_ecefArc_init(self):
        """Test initialisation of EcefArc class."""

        result_1 = np.arctan(2.0)
        for i in range(11):
            a = EcefPoint(ECEF_ICOSAHEDRON[i])
            b = EcefPoint(ECEF_ICOSAHEDRON[i + 1])
            arc = EcefArc(a, b)
            assert_array_almost_equal(arc.coords[0], a)
            assert_array_almost_equal(arc.a, a)
            assert_almost_equal(abs(EcefPoint(arc.pole)), 1.0)
            assert_almost_equal(result_1, arc.length)

        # Test zero length arc
        a = EcefPoint(ECEF_ICOSAHEDRON[5])
        arc = EcefArc(a, a)
        assert_array_almost_equal(arc.coords[0], a)
        assert_array_almost_equal(arc.a, a)
        self.assertFalse(EcefPoint(arc.pole))
        self.assertEqual(arc.length, 0.0)

        # Test antipodal points
        a = EcefPoint(ECEF_ICOSAHEDRON[0])
        b = EcefPoint(ECEF_ICOSAHEDRON[11])
        arc = EcefArc(a, b)
        assert_array_almost_equal(arc.coords[0], a)
        assert_array_almost_equal(arc.a, a)
        self.assertFalse(EcefPoint(arc.pole))
        assert_almost_equal(arc.length, np.pi)

    def test_repr(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        arc = EcefArc(ecef_point_0, ecef_point_1)
        self.assertEqual('EcefArc([[ 0.  0.  1.]\n [ 0. -1.  0.]],1.1071487172337777)',
                         repr(arc))

    def test_str(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        arc = EcefArc(ecef_point_0, ecef_point_1)
        self.assertEqual('EcefArc([[ 0.  0.  1.]\n [ 0. -1.  0.]],1.1071487172337777)',
                         str(arc))

    def test_eq(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        a = EcefArc(ecef_point_0, ecef_point_1)
        b = EcefArc(ecef_point_1, ecef_point_0)

        self.assertTrue(a == a)
        self.assertTrue(b == b)
        self.assertFalse(a == b)
        self.assertFalse(b == a)

    def test_bool(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        a = EcefArc(ecef_point_0, ecef_point_1)
        b = EcefArc(ecef_point_1, ecef_point_1)  # a null arc

        self.assertTrue(a)
        self.assertFalse(b)

    def test_position(self):
        ecef_equator_1 = EcefPoint([1.0, 0.0, 0.0])
        ecef_equator_2 = EcefPoint([0.0, 1.0, 0.0])
        arc = EcefArc(ecef_equator_1, ecef_equator_2)

        assert_array_almost_equal(arc.position(0.0), ecef_equator_1)
        assert_array_almost_equal(arc.position(arc.length), ecef_equator_2)

        recp_sqrt_2 = 1.0 / np.sqrt(2.0)
        ecef_equator_half = EcefPoint([recp_sqrt_2, recp_sqrt_2, 0.0])
        assert_array_almost_equal(arc.position(arc.length / 2),
                                  ecef_equator_half)

        ecef_equator_3 = EcefPoint([0.0, -1.0, 0.0])
        assert_array_almost_equal(arc.position(-arc.length), ecef_equator_3)

        ecef_equator_4 = EcefPoint([-1.0, 0.0, 0.0])
        assert_array_almost_equal(arc.position(2 * arc.length), ecef_equator_4)

    def test_perp_position(self):
        ecef_equator_1 = EcefPoint([1.0, 0.0, 0.0])
        ecef_equator_2 = EcefPoint([0.0, 1.0, 0.0])
        arc = EcefArc(ecef_equator_1, ecef_equator_2)

        assert_array_almost_equal(arc.perp_position(ecef_equator_1, 0.0),
                                  ecef_equator_1)
        assert_array_almost_equal(arc.perp_position(ecef_equator_2, 0.0),
                                  ecef_equator_2)

        distance = np.deg2rad(1.0)
        perp_pos1 = arc.perp_position(ecef_equator_1, distance)
        assert_almost_equal(arc.along_track_distance(perp_pos1), 0.0)
        assert_almost_equal(arc.cross_track_distance(perp_pos1), distance)

        perp_pos2 = arc.perp_position(ecef_equator_1, -distance)
        assert_almost_equal(arc.along_track_distance(perp_pos2), 0.0)
        assert_almost_equal(arc.cross_track_distance(perp_pos2), -distance)

        perp_pos3 = arc.perp_position(ecef_equator_2, distance)
        assert_almost_equal(arc.along_track_distance(perp_pos3), arc.length)
        assert_almost_equal(arc.cross_track_distance(perp_pos3), distance)

        perp_pos4 = arc.perp_position(ecef_equator_2, -distance)
        assert_almost_equal(arc.along_track_distance(perp_pos4), arc.length)
        assert_almost_equal(arc.cross_track_distance(perp_pos4), -distance)

    def test_cross_track_distance(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        arc = EcefArc(ecef_point_0, ecef_point_1)

        self.assertEqual(arc.cross_track_distance(ecef_point_0), 0.0)
        self.assertEqual(arc.cross_track_distance(ecef_point_1), 0.0)

        result2 = 0.5 * (np.pi - np.arctan(2.0))
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[2])
        assert_almost_equal(arc.cross_track_distance(ecef_point_2), result2)

        result3 = 0.5 * np.arctan(2.0)
        ecef_point_3 = EcefPoint(ECEF_ICOSAHEDRON[3])
        assert_almost_equal(arc.cross_track_distance(ecef_point_3), result3)
        ecef_point_4 = EcefPoint(ECEF_ICOSAHEDRON[4])
        assert_almost_equal(arc.cross_track_distance(ecef_point_4), -result3)

        ecef_point_5 = EcefPoint(ECEF_ICOSAHEDRON[5])
        assert_almost_equal(arc.cross_track_distance(ecef_point_5), -result2)

        ecef_point_6 = EcefPoint(ECEF_ICOSAHEDRON[6])
        assert_almost_equal(arc.cross_track_distance(ecef_point_6), -result3)
        ecef_point_7 = EcefPoint(ECEF_ICOSAHEDRON[7])
        assert_almost_equal(arc.cross_track_distance(ecef_point_7), result3)

        ecef_point_8 = EcefPoint(ECEF_ICOSAHEDRON[8])
        assert_almost_equal(arc.cross_track_distance(ecef_point_8), result2)

        ecef_point_9 = EcefPoint(ECEF_ICOSAHEDRON[9])
        assert_almost_equal(arc.cross_track_distance(ecef_point_9), 0.0)

        ecef_point_10 = EcefPoint(ECEF_ICOSAHEDRON[10])
        assert_almost_equal(arc.cross_track_distance(ecef_point_10), -result2)

        ecef_point_11 = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(arc.cross_track_distance(ecef_point_11), 0.0)

    def test_along_track_distance(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[0])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[1])
        arc = EcefArc(ecef_point_0, ecef_point_1)

        self.assertEqual(arc.along_track_distance(ecef_point_0), 0.0)

        result1 = np.arctan(2.0)
        assert_almost_equal(arc.along_track_distance(ecef_point_1), result1)

        result2 = 0.5 * np.arctan(2.0)
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[2])
        assert_almost_equal(arc.along_track_distance(ecef_point_2), result2)

        result3 = 0.5 * (np.arctan(2.0) - np.pi)
        ecef_point_3 = EcefPoint(ECEF_ICOSAHEDRON[3])
        assert_almost_equal(arc.along_track_distance(ecef_point_3), result3)
        ecef_point_4 = EcefPoint(ECEF_ICOSAHEDRON[4])
        assert_almost_equal(arc.along_track_distance(ecef_point_4), result3)

        ecef_point_5 = EcefPoint(ECEF_ICOSAHEDRON[5])
        assert_almost_equal(arc.along_track_distance(ecef_point_5), result2)

        result4 = 2.124370686
        ecef_point_6 = EcefPoint(ECEF_ICOSAHEDRON[6])
        assert_almost_equal(arc.along_track_distance(ecef_point_6), result4)
        ecef_point_7 = EcefPoint(ECEF_ICOSAHEDRON[7])
        assert_almost_equal(arc.along_track_distance(ecef_point_7), result4)

        result5 = 0.5 * np.arctan(2.0) - np.pi
        ecef_point_8 = EcefPoint(ECEF_ICOSAHEDRON[8])
        assert_almost_equal(arc.along_track_distance(ecef_point_8), result5)

        result6 = np.arctan(2.0) - np.pi
        ecef_point_9 = EcefPoint(ECEF_ICOSAHEDRON[9])
        assert_almost_equal(arc.along_track_distance(ecef_point_9), result6)

        ecef_point_10 = EcefPoint(ECEF_ICOSAHEDRON[10])
        assert_almost_equal(arc.along_track_distance(ecef_point_10), result5)

        ecef_point_11 = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(arc.along_track_distance(ecef_point_11), np.pi)

        # Test points at poles.
        ecef_equator_1 = EcefPoint([1.0, 0.0, 0.0])
        ecef_equator_2 = EcefPoint([0.0, 1.0, 0.0])
        arc = EcefArc(ecef_equator_1, ecef_equator_2)

        north_pole = EcefPoint(ECEF_ICOSAHEDRON[0])
        assert_almost_equal(arc.along_track_distance(north_pole), 0.0)

        south_pole = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(arc.along_track_distance(south_pole), 0.0)

    def test_closest_distance(self):
        ecef_equator_1 = EcefPoint([1.0, 0.0, 0.0])
        ecef_equator_2 = EcefPoint([0.0, 1.0, 0.0])
        arc = EcefArc(ecef_equator_1, ecef_equator_2)

        assert_almost_equal(arc.closest_distance(ecef_equator_1), 0.0)
        assert_almost_equal(arc.closest_distance(ecef_equator_2), 0.0)

        ecef_vector_4 = EcefPoint(ECEF_ICOSAHEDRON[4])
        assert_almost_equal(arc.closest_distance(ecef_vector_4),
                            0.463647609561)
        ecef_vector_7 = EcefPoint(ECEF_ICOSAHEDRON[7])
        assert_almost_equal(arc.closest_distance(ecef_vector_7),
                            2.1243706866836156)

        north_pole = EcefPoint(ECEF_ICOSAHEDRON[0])
        assert_almost_equal(arc.closest_distance(north_pole), np.pi / 2)

        south_pole = EcefPoint(ECEF_ICOSAHEDRON[11])
        assert_almost_equal(arc.closest_distance(south_pole), np.pi / 2)

    def test_turn_angle(self):

        result_1 = 0.6 * np.pi
        result_2 = 0.2 * np.pi

        a = EcefPoint(ECEF_ICOSAHEDRON[0])
        b = EcefPoint(ECEF_ICOSAHEDRON[1])
        arc = EcefArc(a, b)

        # test zero distance to b
        angle = arc.turn_angle(b)
        self.assertEqual(angle, 0.0)

        # test zero angle, along IDL from North Pole to South Pole
        c = EcefPoint(ECEF_ICOSAHEDRON[11])
        angle = arc.turn_angle(c)
        self.assertEqual(angle, 0.0)

        for i in range(10):
            a = EcefPoint(ECEF_ICOSAHEDRON[i])
            b = EcefPoint(ECEF_ICOSAHEDRON[i + 1])
            arc = EcefArc(a, b)

            c = EcefPoint(ECEF_ICOSAHEDRON[i + 2])

            angle = arc.turn_angle(c)

            if i == 0:
                assert_almost_equal(angle, -result_1)
            elif i == 9:
                assert_almost_equal(angle, result_1)
            elif i == 4 or i >= 6:
                assert_almost_equal(angle, result_2)
            else:  # elif i == 1:
                assert_almost_equal(angle, -result_2)


if __name__ == '__main__':
    unittest.main()
