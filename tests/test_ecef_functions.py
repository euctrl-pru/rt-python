#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import pandas as pd
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.EcefPoint import *
from pru.ecef_functions import *

GOLDEN_ANGLE = np.arctan(2.0)
LATITUDE = 90.0 - np.rad2deg(GOLDEN_ANGLE)

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


class TestEcefFunctions(unittest.TestCase):

    def test_calculate_EcefPoints(self):
        'Test conversion of Icosahedron Lat Long verticies.'

        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])
        for i in range(12):
            ecef_point = ecef_points[i]

            expected_result = ECEF_ICOSAHEDRON[i]
            assert_array_almost_equal(ecef_point.coords, expected_result)

    def test_calculate_leg_lengths(self):
        'Test calculation of Icosahedron edge lengths.'

        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])
        chord_lengths = calculate_leg_lengths(ecef_points)
        self.assertEqual(chord_lengths[0], 0.0)

        expected_result = GOLDEN_ANGLE
        for i in range(1, 12):
            assert_array_almost_equal(chord_lengths[i], expected_result)

    def test_calculate_distances(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        # Test North pole to South pole
        distances = calculate_distances(ecef_points, ecef_points[0])
        self.assertEqual(len(distances), 12)

        # North Pole
        self.assertEqual(distances[0], 0.0)

        # The 5 verticies North of the Equator
        result1 = GOLDEN_ANGLE
        for i in range(1, 6):
            assert_almost_equal(distances[i], result1)

        # The 5 verticies South of the Equator
        result2 = np.pi - GOLDEN_ANGLE
        for i in range(6, 11):
            assert_almost_equal(distances[i], result2)

        # South Pole
        self.assertEqual(distances[11], np.pi)

    def test_find_furthest_distance(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        # Test North pole to South pole
        distance1, index1 = find_furthest_distance(ecef_points)
        self.assertEqual(index1, 11)

        # Test around Northern Hemisphere
        northern_points = ecef_points[range(1, 6)]
        distance2, index2 = find_furthest_distance(northern_points)
        self.assertEqual(index2, 2)

    def test_calculate_position(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        point_0 = calculate_position(ecef_points, 0)
        self.assertEqual(point_0, ecef_points[0])

        point_11 = calculate_position(ecef_points, 11)
        self.assertEqual(point_11, ecef_points[-1])

        point_11_5 = calculate_position(ecef_points, 11, ratio=0.5)
        self.assertEqual(point_11, ecef_points[-1])

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

    def test_calculate_xtds(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])
        arc = EcefArc(ecef_points[0], ecef_points[1])
        xtds = calculate_xtds(arc, ecef_points)

        # North Pole
        self.assertEqual(xtds[0], 0.0)

        # The 5 verticies North of the Equator
        self.assertEqual(xtds[1], 0.0)

        result2 = 0.5 * (np.pi - np.arctan(2.0))
        assert_almost_equal(xtds[2], result2)

        result3 = 0.5 * np.arctan(2.0)
        assert_almost_equal(xtds[3], result3)
        assert_almost_equal(xtds[4], -result3)

        assert_almost_equal(xtds[5], -result2)

        # The 5 verticies North of the Equator
        assert_almost_equal(xtds[6], -result3)
        assert_almost_equal(xtds[7], result3)

        assert_almost_equal(xtds[8], result2)

        assert_almost_equal(xtds[9], 0.0)

        assert_almost_equal(xtds[10], -result2)

        # South Pole
        self.assertEqual(xtds[11], 0.0)

    def test_calculate_atds(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])
        arc = EcefArc(ecef_points[0], ecef_points[1])
        atds = calculate_atds(arc, ecef_points)

        # North Pole
        self.assertEqual(atds[0], 0.0)

        # The 5 verticies North of the Equator
        result1 = np.arctan(2.0)
        assert_almost_equal(atds[1], result1)

        result2 = 0.5 * np.arctan(2.0)
        assert_almost_equal(atds[2], result2)

        result3 = 0.5 * (np.arctan(2.0) - np.pi)
        assert_almost_equal(atds[3], result3)
        assert_almost_equal(atds[4], result3)

        assert_almost_equal(atds[5], result2)

        # The 5 verticies South of the Equator
        result4 = 2.124370686
        assert_almost_equal(atds[6], result4)
        assert_almost_equal(atds[7], result4)

        result5 = 0.5 * np.arctan(2.0) - np.pi
        assert_almost_equal(atds[8], result5)

        result6 = np.arctan(2.0) - np.pi
        assert_almost_equal(atds[9], result6)

        assert_almost_equal(atds[10], result5)

        # South Pole
        self.assertEqual(atds[11], np.pi)

    def test_find_most_extreme_value(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])
        arc = EcefArc(ecef_points[3], ecef_points[8])
        xtds = calculate_xtds(arc, ecef_points)

        assert_almost_equal(xtds[3], 0.0)
        assert_almost_equal(xtds[8], 0.0)

        xtds_4_8 = xtds[3: 9]
        self.assertEqual(len(xtds_4_8), 6)

        max_xtd, max_xtd_index = find_most_extreme_value(xtds_4_8)
        assert_almost_equal(max_xtd, 0.55357435)
        self.assertEqual(max_xtd_index, 1)

    def test_calculate_EcefArcs(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        ecef_arcs = calculate_EcefArcs(ecef_points)

        self.assertEqual(len(ecef_arcs), 11)

        arc_length = np.arctan(2.0)
        for i in range(len(ecef_arcs)):
            assert_almost_equal(ecef_arcs[i].length, arc_length)
            pole = EcefPoint(ecef_arcs[i].pole)
            assert_almost_equal(pole.norm(), 1.0)

    def test_calculate_closest_distances(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        ecef_arcs = calculate_EcefArcs(ecef_points)

        distances = calculate_closest_distances(ecef_arcs, ecef_points[6])
        min_value_index = distances.argmin()
        self.assertEqual(min_value_index, 6)
        min_value = distances[min_value_index]
        self.assertEqual(min_value, 0.0)

    def test_find_index_and_ratio(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
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

    def test_calculate_turn_angles(self):
        ecef_points = calculate_EcefPoints(PANDAS_ICOSAHEDRON['LAT'],
                                           PANDAS_ICOSAHEDRON['LON'])

        ecef_arcs = calculate_EcefArcs(ecef_points)
        turn_angles = calculate_turn_angles(ecef_arcs)

        self.assertEqual(len(turn_angles), 12)

        # First amd last turn angles are always zero
        self.assertEqual(turn_angles[0], 0.0)
        self.assertEqual(turn_angles[11], 0.0)

        result_1 = 0.6 * np.pi
        result_2 = 0.2 * np.pi
        for i in range(1, 11):
            if i == 1:
                assert_almost_equal(turn_angles[i], -result_1)
            elif i == 10:
                assert_almost_equal(turn_angles[i], result_1)
            elif i == 5 or i >= 7:
                assert_almost_equal(turn_angles[i], result_2)
            else:
                assert_almost_equal(turn_angles[i], -result_2)


if __name__ == '__main__':
    unittest.main()
