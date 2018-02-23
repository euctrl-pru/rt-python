#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.EcefPoint import *
from pru.EcefArc import *
from pru.TurnArc import *

TWENTY_NM = np.deg2rad(1.0 / 3.0)

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


class TestTurnArc(unittest.TestCase):

    def test_calculate_radius(self):

        # 90 degrees
        radius = calculate_radius(np.pi / 2.0, TWENTY_NM)
        assert_almost_equal(radius, TWENTY_NM)

        # 120 degrees
        radius = calculate_radius(MAX_TURN_ANGLE, TWENTY_NM)
        assert_almost_equal(radius, TWENTY_NM / 1.732)

        # 60 degrees
        radius = calculate_radius(np.pi / 3.0, TWENTY_NM)
        assert_almost_equal(radius, TWENTY_NM / 0.57735)

        # 1 degree
        radius = calculate_radius(MIN_TURN_ANGLE, TWENTY_NM)
        assert_almost_equal(radius, TWENTY_NM / 0.00872686779)

    def test_calculate_radius(self):

        # zerodegrees
        arc_length = calculate_arc_length(0.0, TWENTY_NM)
        assert_almost_equal(arc_length, 2.0 * TWENTY_NM)

        # 90 degrees
        arc_length = calculate_arc_length(np.pi / 2.0, TWENTY_NM)
        assert_almost_equal(arc_length, TWENTY_NM * np.pi / 2.0)

    def test_TurnArc_init(self):
        """Test initialisation of TurnArc class."""
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[2])
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[3])
        arc_0 = EcefArc(ecef_point_0, ecef_point_1)
        arc_1 = EcefArc(ecef_point_1, ecef_point_2)

        turn_0 = TurnArc(arc_0, arc_1, TWENTY_NM)
        self.assertTrue(turn_0)

        #  Ensure Turn start and end points are along inbound and outbound arcs
        assert_almost_equal(distance_nm(ecef_point_1, EcefPoint(turn_0.start)), 20.0)
        assert_almost_equal(distance_nm(ecef_point_1, EcefPoint(turn_0.finish)), 20.0)

        assert_almost_equal(arc_0.cross_track_distance(turn_0.start), 0.0)
        assert_almost_equal(arc_1.cross_track_distance(turn_0.finish), 0.0)

        ANGLE = 0.2 * np.pi
        RADIUS = 20.0 / np.tan(ANGLE / 2.0)  # 61.553670693462841 NM

        assert_almost_equal(turn_0.angle, -ANGLE)
        assert_almost_equal(rad2nm(turn_0.radius), RADIUS)
        assert_almost_equal(rad2nm(turn_0.length()), RADIUS * ANGLE)

        assert_almost_equal(turn_0.radial_distance(EcefPoint(turn_0.start)),
                            turn_0.radius, decimal=6)
        assert_almost_equal(turn_0.radial_distance(EcefPoint(turn_0.finish)),
                            turn_0.radius, decimal=6)
        DISTANCE = TWENTY_NM / np.sin(ANGLE / 2.0)  # 64.721359549995796 NM
        assert_almost_equal(turn_0.radial_distance(ecef_point_1), DISTANCE)

        assert_almost_equal(turn_0.cross_track_distance(EcefPoint(turn_0.start)),
                            0.0, decimal=6)
        assert_almost_equal(turn_0.cross_track_distance(EcefPoint(turn_0.finish)),
                            0.0, decimal=6)
        assert_almost_equal(turn_0.cross_track_distance(ecef_point_1),
                            DISTANCE - turn_0.radius)

        self.assertEqual(turn_0.point_angle(EcefPoint(turn_0.centre)), 0.0)
        assert_almost_equal(turn_0.point_angle(EcefPoint(turn_0.start)), 0.0)
        assert_almost_equal(turn_0.point_angle(EcefPoint(turn_0.finish)),
                            turn_0.angle, decimal=4)
        assert_almost_equal(turn_0.point_angle(ecef_point_1), turn_0.angle / 2.0,
                            decimal=4)

        assert_almost_equal(turn_0.along_track_distance(EcefPoint(turn_0.start)), 0.0)
        assert_almost_equal(turn_0.along_track_distance(EcefPoint(turn_0.finish)),
                            turn_0.length(), decimal=6)
        assert_almost_equal(turn_0.along_track_distance(ecef_point_1),
                            turn_0.length() / 2.0, decimal=6)

        pos_1 = turn_0.position(turn_0.angle)
        assert_almost_equal(distance_radians(pos_1, EcefPoint(turn_0.centre)),
                            turn_0.radius)
        assert_almost_equal(distance_radians(pos_1, EcefPoint(turn_0.finish)), 0.0,
                            decimal=6)

        pos_2 = turn_0.position(turn_0.angle / 2.0)
        assert_almost_equal(distance_radians(pos_2, EcefPoint(turn_0.centre)),
                            turn_0.radius)
        assert_almost_equal(turn_0.point_angle(pos_2), turn_0.angle / 2.0)

    def test_TurnArc_invalid_init(self):
        """Test initialisation of TurnArc class."""
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[2])
        arc_0 = EcefArc(ecef_point_0, ecef_point_1)
        arc_1 = EcefArc(ecef_point_1, ecef_point_0)

        turn_0 = TurnArc(arc_0, arc_1, TWENTY_NM)
        self.assertFalse(turn_0)

        #  Ensure Turn start, centre and end points are at waypoint
        assert_almost_equal(distance_nm(ecef_point_1, EcefPoint(turn_0.start)), 0.0)
        assert_almost_equal(distance_nm(ecef_point_1, EcefPoint(turn_0.centre)), 0.0)
        assert_almost_equal(distance_nm(ecef_point_1, EcefPoint(turn_0.finish)), 0.0)

    def test_repr(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[2])
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[3])
        arc_0 = EcefArc(ecef_point_0, ecef_point_1)
        arc_1 = EcefArc(ecef_point_1, ecef_point_2)

        turn_0 = TurnArc(arc_0, arc_1, TWENTY_NM)
        repr_0 = repr(turn_0)
        self.assertEqual('TurnArc([[', repr_0[:10])

    def test_str(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[2])
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[3])
        arc_0 = EcefArc(ecef_point_0, ecef_point_1)
        arc_1 = EcefArc(ecef_point_1, ecef_point_2)

        turn_0 = TurnArc(arc_0, arc_1, TWENTY_NM)
        str_0 = str(turn_0)
        self.assertEqual('TurnArc(', str_0[:8])

    def test_eq(self):
        ecef_point_0 = EcefPoint(ECEF_ICOSAHEDRON[1])
        ecef_point_1 = EcefPoint(ECEF_ICOSAHEDRON[2])
        ecef_point_2 = EcefPoint(ECEF_ICOSAHEDRON[3])
        arc_0 = EcefArc(ecef_point_0, ecef_point_1)
        arc_1 = EcefArc(ecef_point_1, ecef_point_2)

        turn_0 = TurnArc(arc_0, arc_1, TWENTY_NM)

        self.assertTrue(turn_0 == turn_0)

        arc_2 = EcefArc(ecef_point_2, ecef_point_1)
        arc_3 = EcefArc(ecef_point_1, ecef_point_0)

        turn_1 = TurnArc(arc_2, arc_3, TWENTY_NM)

        self.assertFalse(turn_0 == turn_1)


if __name__ == '__main__':
    unittest.main()
