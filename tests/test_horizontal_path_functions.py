#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import pandas as pd
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from os import environ as env
from pru.EcefPoint import rad2nm
from pru.TurnArc import TurnArc
from pru.ecef_functions import *
from pru.horizontal_path_functions import *

TEST_DATA_HOME = 'TEST_DATA_HOME'

ROUTE_LATS = np.array([45.0, 46.0, 47.0, 48.0, 49.0, 50.0,
                       51.0, 52.0, 53.0, 54.0, 55.0, 56.0])
ROUTE_LONS = np.array([-1.0, -1.0, 1.0, 1.0, -1.0, -1.0,
                       1.0, 1.0, -1.0, -1.0, 1.0, 1.0])

ACROSS_TRACK_TOLERANCE = np.deg2rad(0.25 / 60.0)


class TestHorizontlPathFunctions(unittest.TestCase):

    def test_find_extreme_point_index_1(self):
        # A line of Lat Longs around the Equator
        LATITUDES = np.zeros(10, dtype=float)
        LONGITUDES = np.array(range(-5, 5), dtype=float)
        ecef_points_0 = calculate_EcefPoints(LATITUDES, LONGITUDES)

        # same point
        max_index = 0
        result_0 = find_extreme_point_index(ecef_points_0, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_0, max_index)

        # adjacent points
        max_index = 1
        result_1 = find_extreme_point_index(ecef_points_0, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_1, max_index)

        # a point inbetween points
        max_index = 2
        result_2 = find_extreme_point_index(ecef_points_0, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_2, max_index)

        # test toward the end
        max_index = 8
        max_index_0 = find_extreme_point_index(ecef_points_0, 2, max_index,
                                               threshold=ACROSS_TRACK_TOLERANCE,
                                               xtd_ratio=0.1)
        self.assertEqual(max_index_0, max_index)

        # move some points alongside the arc
        LATITUDES[1] = 0.5
        LATITUDES[4] = 1
        ecef_points_1 = calculate_EcefPoints(LATITUDES, LONGITUDES)

        max_index = 2
        result_2 = find_extreme_point_index(ecef_points_1, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_2, 1)

        max_index = 8
        max_index_1 = find_extreme_point_index(ecef_points_1, 0, max_index,
                                               threshold=ACROSS_TRACK_TOLERANCE,
                                               xtd_ratio=0.1)
        self.assertEqual(max_index_1, 4)

        LATITUDES[4] = -1
        ecef_points_2 = calculate_EcefPoints(LATITUDES, LONGITUDES)
        max_index_2 = find_extreme_point_index(ecef_points_2, 2, max_index,
                                               threshold=ACROSS_TRACK_TOLERANCE,
                                               xtd_ratio=0.1)
        self.assertEqual(max_index_2, 4)

        max_index_3 = find_extreme_point_index(ecef_points_2, 2, max_index,
                                               threshold=np.deg2rad(1.0),
                                               xtd_ratio=0.1)
        self.assertEqual(max_index_3, 4)

        SHORT_LONGITUDES = np.array([-5 + i / 600.0 for i in range(10)], dtype=float)
        ecef_points_4 = calculate_EcefPoints(LATITUDES, SHORT_LONGITUDES)

        max_index_4 = find_extreme_point_index(ecef_points_4, 2, max_index,
                                               threshold=ACROSS_TRACK_TOLERANCE,
                                               xtd_ratio=0.1)
        self.assertEqual(max_index_2, 4)

    def test_find_extreme_point_index_2(self):
        # A line of Lat Longs by the Equator
        LATITUDES = np.array([0.0, -0.001, 0.01, -0.001, 0.0])
        LONGITUDES = np.array([0.0, 0.0005, 0.001, 0.0014, 0.0015])
        ecef_points_0 = calculate_EcefPoints(LATITUDES, LONGITUDES)

        # mid point
        max_index = len(ecef_points_0) - 1
        result_0 = find_extreme_point_index(ecef_points_0, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_0, 2)

        # first half
        max_index = 2
        result_1 = find_extreme_point_index(ecef_points_0, 0, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_1, 2)

        # second half
        max_index = len(ecef_points_0) - 1
        result_2 = find_extreme_point_index(ecef_points_0, 2, max_index,
                                            threshold=ACROSS_TRACK_TOLERANCE,
                                            xtd_ratio=0.1)
        self.assertEqual(result_2, max_index)

    def test_find_extreme_point_indicies(self):
        # A line of Lat Longs around the Equator
        LATITUDES = np.zeros(10, dtype=float)
        LONGITUDES = np.array([-5 + i for i in range(10)], dtype=float)
        ecef_points_0 = calculate_EcefPoints(LATITUDES, LONGITUDES)

        indicies_0 = find_extreme_point_indicies(ecef_points_0,
                                                 threshold=ACROSS_TRACK_TOLERANCE,
                                                 xtd_ratio=0.1)

        self.assertEqual(len(indicies_0), 2)
        assert_array_almost_equal(indicies_0, [0, 9])

        LATITUDES[4] = 1
        LATITUDES[8] = -1
        ecef_points_1 = calculate_EcefPoints(LATITUDES, LONGITUDES)

        indicies_1 = find_extreme_point_indicies(ecef_points_1,
                                                 threshold=ACROSS_TRACK_TOLERANCE,
                                                 xtd_ratio=0.1)
        self.assertEqual(len(indicies_1), 7)
        assert_array_almost_equal(indicies_1, [0, 3, 4, 5, 7, 8, 9])

        indicies_3 = find_extreme_point_indicies(ecef_points_1,
                                                 threshold=np.deg2rad(1.0),
                                                 xtd_ratio=0.1)
        self.assertEqual(len(indicies_3), 7)
        # assert_array_almost_equal(indicies_3, [0, 9])

    def test_fit_arc_to_points(self):
        LATS_0 = np.zeros(4, dtype=np.float)
        LONS_0 = np.array([0.0, 1.0, 2.0, 3.0])

        # Test points along arc
        ecef_points_0 = calculate_EcefPoints(LATS_0, LONS_0)
        ecef_arc_0 = EcefArc(ecef_points_0[0], ecef_points_0[-1])
        new_arc_0 = fit_arc_to_points(ecef_points_0, ecef_arc_0)
        assert_array_almost_equal(new_arc_0.a, ecef_arc_0.a)
        assert_array_almost_equal(new_arc_0.b, ecef_arc_0.b)

        # Test slope away from start of arc
        ecef_points_1 = calculate_EcefPoints(LONS_0, LONS_0)
        ecef_arc_1 = EcefArc(ecef_points_1[0], ecef_points_1[-1])

        new_arc_1 = fit_arc_to_points(ecef_points_1, ecef_arc_0)
        assert_array_almost_equal(new_arc_1.a, ecef_arc_0.a)
        assert_array_almost_equal(new_arc_1.pole, ecef_arc_1.pole)

        # Test slope towards end of arc
        LATS_2 = np.array([3.0, 2.0, 1.0, 0.0])
        ecef_points_2 = calculate_EcefPoints(LATS_2, LONS_0)
        ecef_arc_2 = EcefArc(ecef_points_2[0], ecef_points_2[-1])

        new_arc_2 = fit_arc_to_points(ecef_points_2, ecef_arc_0)
        assert_array_almost_equal(new_arc_2.pole, ecef_arc_2.pole)
        assert_array_almost_equal(new_arc_2.b, ecef_arc_0.b)

    def test_calculate_intersection(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        # intersection point between arcs on different Great Circles
        prev_arc = EcefArc(ecef_points[0], ecef_points[1])
        arc = EcefArc(ecef_points[1], ecef_points[2])
        point_1 = calculate_intersection(prev_arc, arc)
        assert_array_almost_equal(point_1, ecef_points[1])

        # intersection point between arcs on same Great Circles
        next_point = arc.position(2 * arc.length)
        next_arc = EcefArc(ecef_points[2], next_point)
        point_2 = calculate_intersection(arc, next_arc)
        assert_array_almost_equal(point_2, ecef_points[2])

        # intersection point between arcs on different Great Circles,
        # opposite direction turn
        prev_arc = EcefArc(ecef_points[5], ecef_points[6])
        arc = EcefArc(ecef_points[6], ecef_points[7])
        point_3 = calculate_intersection(prev_arc, arc)
        assert_array_almost_equal(point_3, ecef_points[6])

    def test_calculate_max_turn_initiation_distance(self):
        # two long legs
        result_1 = calculate_max_turn_initiation_distance(np.deg2rad(2.0 / 3.0),
                                                          np.deg2rad(1.0))
        self.assertEqual(result_1, TWENTY_NM)

        # first leg is short
        result_2 = calculate_max_turn_initiation_distance(TWO_NM,
                                                          np.deg2rad(1.0))
        self.assertEqual(result_2, TWO_NM / 2)

        # second leg is short
        result_3 = calculate_max_turn_initiation_distance(np.deg2rad(2.0 / 3.0),
                                                          TWO_NM)
        self.assertEqual(result_3, TWO_NM / 2)

    def test_calculate_turn_initiation_distance_90(self):
        # A 90 degree turn at the Equator
        LATS = np.array([0.0, 0.0, 1.0])
        LONS = np.array([1.0, 0.0, 0.0])
        ecef_points = calculate_EcefPoints(LATS, LONS)

        prev_arc = EcefArc(ecef_points[0], ecef_points[1])
        arc = EcefArc(ecef_points[1], ecef_points[2])
        TEN_NM = TWENTY_NM / 2
        turn_0 = TurnArc(prev_arc, arc, TEN_NM)
        turn_angle_0 = turn_0.angle

        distance_start = calculate_turn_initiation_distance(prev_arc, arc, turn_0.start,
                                                            TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_start, TEN_NM)

        distance_finish = calculate_turn_initiation_distance(prev_arc, arc, turn_0.finish,
                                                             TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_finish, TEN_NM)

        point_1 = turn_0.position(turn_angle_0 / 2)
        distance_1 = calculate_turn_initiation_distance(prev_arc, arc, point_1,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_1, TEN_NM)

        point_2 = turn_0.position(turn_angle_0 / 4)
        distance_2 = calculate_turn_initiation_distance(prev_arc, arc, point_2,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_2, TEN_NM)

        point_3 = turn_0.position(3 * turn_angle_0 / 4)
        distance_3 = calculate_turn_initiation_distance(prev_arc, arc, point_3,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_3, TEN_NM)

        # Test with a point further than TWENTY_NM from the intersection
        turn_30 = TurnArc(prev_arc, arc, TWENTY_NM + TEN_NM)
        distance_4 = calculate_turn_initiation_distance(prev_arc, arc, turn_30.start,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        self.assertEqual(distance_4, TWENTY_NM)

        point_30 = turn_30.position(3 * turn_angle_0 / 4)
        distance_30 = calculate_turn_initiation_distance(prev_arc, arc, point_30,
                                                         TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        self.assertEqual(distance_30, TWENTY_NM)

    def test_calculate_turn_initiation_distance_20(self):
        # A shallow turn at the Equator
        LATS = np.array([0.0, 0.0, 0.2])
        LONS = np.array([-1.0, 0.0, 1.0])
        ecef_points = calculate_EcefPoints(LATS, LONS)

        prev_arc = EcefArc(ecef_points[0], ecef_points[1])
        arc = EcefArc(ecef_points[1], ecef_points[2])
        TEN_NM = TWENTY_NM / 2
        turn_0 = TurnArc(prev_arc, arc, TEN_NM)
        turn_angle_0 = turn_0.angle

        distance_start = calculate_turn_initiation_distance(prev_arc, arc, turn_0.start,
                                                            TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_start, TEN_NM)

        distance_finish = calculate_turn_initiation_distance(prev_arc, arc, turn_0.finish,
                                                             TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_finish, TEN_NM)

        point_1 = turn_0.position(turn_angle_0 / 2)
        distance_1 = calculate_turn_initiation_distance(prev_arc, arc, point_1,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE)
        assert_almost_equal(distance_1, TEN_NM, decimal=6)

        point_2 = turn_0.position(turn_angle_0 / 4)
        distance_2 = calculate_turn_initiation_distance(prev_arc, arc, point_2,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE / 4)
        assert_almost_equal(distance_2, TEN_NM, decimal=6)

        point_3 = turn_0.position(3 * turn_angle_0 / 4)
        distance_3 = calculate_turn_initiation_distance(prev_arc, arc, point_3,
                                                        TWENTY_NM, ACROSS_TRACK_TOLERANCE / 4)
        assert_almost_equal(distance_3, TEN_NM, decimal=5)

    def test_derive_horizontal_path(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)
        ecef_path = derive_horizontal_path(ecef_points, ACROSS_TRACK_TOLERANCE)
        self.assertEqual(len(ecef_path), 12)
        assert_array_almost_equal(ecef_path.points[0], ecef_points[0])
        assert_array_almost_equal(ecef_path.points[-1], ecef_points[-1])


if __name__ == '__main__':
    unittest.main()
