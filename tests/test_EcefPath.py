#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.EcefPoint import rad2nm
from pru.ecef_functions import *
from pru.EcefPath import *

NM = np.deg2rad(1.0 / 60.0)

ROUTE_LATS = np.array([1.0, 1.0, 1.0, -1.0, -1.0, 1.0,
                       1.0, 0.0, 0.0, 1.0, 2.0, 3.0])
ROUTE_LONS = np.array([-3.0, -2.0, -1.0, -1.0, 1.0, 0.0,
                       3.0, 2.0, 5.0, 4.0, 4.0, 4.0])

TURN_DISTANCES = np.array([0., 0., 10 * NM, 20 * NM, 20 * NM, 20 * NM,
                           20 * NM, 20 * NM, 20 * NM, 20 * NM, 0., 0.])

EXPECTED_LEG_LENGTHS = [0.,   59.99086148,   59.99086148,  120.,
                        119.98172156,  134.16271632,  179.97257886,   84.85065966,
                        180.,   84.85065966,   60.,   60.]

EXPECTED_TURN_ANGLES = [0., 0., 89.99127358, -89.98254582,
                        -116.54934239, 116.54061198, 134.97817895, -134.99563646,
                        -134.99563646, 45.00436354,  0., 0.]

EXPECTED_PATH_LENGTHS = [0., 59.99086148, 57.84527776, 113.56411819,
                         108.267138, 119.31534542, 162.31284918, 64.37442822,
                         159.52082563, 73.57205787, 58.9609854, 60.]

EXPECTED_PATH_DISTANCES = [0., 59.99086148, 117.83613924, 231.40025743,
                           339.66739543, 458.98274085, 621.29559004, 685.67001826,
                           845.19084389, 918.76290176, 977.72388715, 1037.723887]


class TestEcefPath(unittest.TestCase):

    def test_EcefPath_init(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        self.assertEqual(len(ecef_path.points), 12)
        assert_array_almost_equal(ecef_path.points, ecef_points)
        self.assertEqual(len(ecef_path.turn_initiation_distances), 12)
        assert_array_almost_equal(ecef_path.turn_initiation_distances, TURN_DISTANCES)
        self.assertEqual(len(ecef_path.leg_lengths), 12)
        assert_array_almost_equal(rad2nm(ecef_path.leg_lengths), EXPECTED_LEG_LENGTHS)
        self.assertEqual(len(ecef_path.turn_angles), 12)
        assert_array_almost_equal(np.rad2deg(ecef_path.turn_angles), EXPECTED_TURN_ANGLES)
        self.assertEqual(len(ecef_path.path_lengths), 12)
        assert_array_almost_equal(rad2nm(ecef_path.path_lengths), EXPECTED_PATH_LENGTHS)

        lats, lons = ecef_path.point_lat_longs()
        assert_array_almost_equal(lats, ROUTE_LATS)
        assert_array_almost_equal(lons, ROUTE_LONS)

        assert_array_almost_equal(ecef_path.turn_initiation_distances_nm(),
                                  rad2nm(TURN_DISTANCES))

    def test_EcefPath_invalid_init(self):
        'The route has a duplicate point in the middle, so closer than MIN_LENGTH'
        INVALID_ROUTE_LATS = np.array([1.0, 1.0, 1.0, 1.0, -1.0, 1.0])
        INVALID_ROUTE_LONS = np.array([-3.0, -2.0, -1.0, -1.0, 1.0, 0.0])
        invalid_points = calculate_EcefPoints(INVALID_ROUTE_LATS, INVALID_ROUTE_LONS)
        zero_distances = np.zeros(len(invalid_points), dtype=float)
        self.assertRaises(ValueError, EcefPath, invalid_points, zero_distances)

    def test_EcefPath_path_distances(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        path_distances = ecef_path.path_distances()
        self.assertEqual(len(path_distances), 12)

        assert_array_almost_equal(rad2nm(path_distances), EXPECTED_PATH_DISTANCES)

    def test_EcefPath_turn_points(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)
        turn_points_0 = ecef_path.turn_points(number_of_points=0)
        self.assertEqual(len(turn_points_0), len(ecef_path) + 8)

        # Ensure that start and end points are along inbound and outboud arcs
        arc_1 = EcefArc(ecef_points[1], ecef_points[2])
        assert_almost_equal(arc_1.cross_track_distance(turn_points_0[2]), 0.0)

        arc_2 = EcefArc(ecef_points[2], ecef_points[3])
        assert_almost_equal(arc_2.cross_track_distance(turn_points_0[3]), 0.0)
        assert_almost_equal(arc_2.cross_track_distance(turn_points_0[4]), 0.0)

        arc_last = EcefArc(ecef_points[-2], ecef_points[-1])
        assert_almost_equal(arc_last.cross_track_distance(turn_points_0[-2]), 0.0)

        turn_points_1 = ecef_path.turn_points(number_of_points=1)
        self.assertEqual(len(turn_points_1), len(ecef_path) + 16)

        turn_points_3 = ecef_path.turn_points()
        self.assertEqual(len(turn_points_3), len(ecef_path) + 32)

        turn_points_5 = ecef_path.turn_points(number_of_points=5)
        self.assertEqual(len(turn_points_5), len(ecef_path) + 48)

    def test_EcefPath_calculate_position(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        pos_0 = ecef_path.calculate_position(0, 0.0)
        assert_array_almost_equal(pos_0, ecef_points[0])

        pos_1 = ecef_path.calculate_position(1, 0.0)
        assert_array_almost_equal(pos_1, ecef_points[1])

        arc2 = EcefArc(ecef_points[1], ecef_points[2])
        arc3 = EcefArc(ecef_points[2], ecef_points[3])

        turn_arc2 = TurnArc(arc2, arc3, TURN_DISTANCES[2])
        turn2_midpoint = EcefPoint(turn_arc2.position(0.5 * abs(turn_arc2.angle)))

        pos_2 = ecef_path.calculate_position(2, 0.000001)
        assert_array_almost_equal(pos_2, turn2_midpoint)

        pos_1_99999 = ecef_path.calculate_position(1, 0.99999)
        assert_array_almost_equal(pos_1_99999, pos_2)

        pos_13 = ecef_path.calculate_position(13, 0.0)
        assert_array_almost_equal(pos_13, ecef_points[-1])

    def test_EcefPath_calculate_path_leg_distance(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        # Start point
        distance_0 = ecef_path.calculate_path_leg_distance(ecef_points[0], 0)
        self.assertEqual(distance_0, 0.0)

        # Point at end of a straight leg
        distance_1_0 = ecef_path.calculate_path_leg_distance(ecef_points[1], 0)
        assert_almost_equal(rad2nm(distance_1_0), EXPECTED_PATH_LENGTHS[1])

        # Point at start of a straight leg
        distance_1_1 = ecef_path.calculate_path_leg_distance(ecef_points[1], 1)
        self.assertEqual(distance_0, 0.0)

        # Point in middle of a straight leg
        pos_1_5 = ecef_path.calculate_position(1, 0.5)
        distance_1_5 = ecef_path.calculate_path_leg_distance(pos_1_5, 1)
        assert_almost_equal(rad2nm(distance_1_5), 0.5 * EXPECTED_PATH_LENGTHS[2])

        # Point toward end of a turning leg
        pos_1_9 = ecef_path.calculate_position(1, 0.99)
        distance_1_9 = ecef_path.calculate_path_leg_distance(pos_1_9, 1)
        assert_almost_equal(rad2nm(distance_1_9), 0.99 * EXPECTED_PATH_LENGTHS[2])

        # Before start of a turning leg
        distance_2_9 = ecef_path.calculate_path_leg_distance(pos_1_9, 2)
        assert_almost_equal(rad2nm(distance_2_9), -0.57845277761762326)

        # Point toward start of a turning leg
        pos_2_1 = ecef_path.calculate_position(2, 0.01)
        distance_2_1 = ecef_path.calculate_path_leg_distance(pos_2_1, 2)
        assert_almost_equal(rad2nm(distance_2_1), 0.01 * EXPECTED_PATH_LENGTHS[3])

        # Past the ned of a turning leg
        distance_1_2 = ecef_path.calculate_path_leg_distance(pos_2_1, 1)
        self.assertTrue(rad2nm(distance_1_2) > EXPECTED_PATH_LENGTHS[2])
        assert_almost_equal(rad2nm(distance_1_2), 58.980918943627351)

        # Point along a turning leg
        pos_2_75 = ecef_path.calculate_position(2, 0.75)
        distance_2_75 = ecef_path.calculate_path_leg_distance(pos_2_75, 2)
        assert_almost_equal(rad2nm(distance_2_75), 0.75 * EXPECTED_PATH_LENGTHS[3])

        # Last point
        distance_last = ecef_path.calculate_path_leg_distance(ecef_points[-1], 10)
        assert_almost_equal(rad2nm(distance_last), EXPECTED_PATH_LENGTHS[11])

    def test_EcefPath_calculate_path_distance(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        # Start point
        distance_0 = ecef_path.calculate_path_distance(ecef_points[0], 0)
        self.assertEqual(distance_0, 0.0)

        # from next leg
        distance_0 = ecef_path.calculate_path_distance(ecef_points[0], 1)
        self.assertEqual(distance_0, 0.0)

        # Point at end of first, straight leg
        distance_1_0 = ecef_path.calculate_path_distance(ecef_points[1], 0)
        assert_almost_equal(rad2nm(distance_1_0), EXPECTED_PATH_DISTANCES[1])

        # from next leg
        distance_1_0 = ecef_path.calculate_path_distance(ecef_points[1], 1)
        assert_almost_equal(rad2nm(distance_1_0), EXPECTED_PATH_DISTANCES[1])

        # from leg after next
        distance_1_0 = ecef_path.calculate_path_distance(ecef_points[1], 2)
        assert_almost_equal(rad2nm(distance_1_0), EXPECTED_PATH_DISTANCES[1])

        # Point in middle of first,  straight leg
        pos_1_5 = ecef_path.calculate_position(1, 0.5)
        distance_1_5 = ecef_path.calculate_path_distance(pos_1_5, 1)
        assert_almost_equal(rad2nm(distance_1_5),
                            EXPECTED_PATH_DISTANCES[1] + 0.5 * EXPECTED_PATH_LENGTHS[2])

        # from previous leg
        distance_1_5 = ecef_path.calculate_path_distance(pos_1_5, 0)
        assert_almost_equal(rad2nm(distance_1_5),
                            EXPECTED_PATH_DISTANCES[1] + 0.5 * EXPECTED_PATH_LENGTHS[2])

        # from next leg
        distance_1_5 = ecef_path.calculate_path_distance(pos_1_5, 2)
        assert_almost_equal(rad2nm(distance_1_5),
                            EXPECTED_PATH_DISTANCES[1] + 0.5 * EXPECTED_PATH_LENGTHS[2])

        # Point along a turning leg
        pos_2_75 = ecef_path.calculate_position(2, 0.75)
        distance_2_75 = ecef_path.calculate_path_distance(pos_2_75, 2)
        assert_almost_equal(rad2nm(distance_2_75),
                            EXPECTED_PATH_DISTANCES[2] + 0.75 * EXPECTED_PATH_LENGTHS[3])

        # Last point
        distance_last = ecef_path.calculate_path_distance(ecef_points[-1], 10)
        assert_almost_equal(rad2nm(distance_last), EXPECTED_PATH_DISTANCES[11],
                            decimal=6)

        # from previous leg
        distance_last = ecef_path.calculate_path_distance(ecef_points[-1], 9)
        assert_almost_equal(rad2nm(distance_last), EXPECTED_PATH_DISTANCES[11],
                            decimal=6)

    def test_EcefPath_calculate_path_distances(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        distances = rad2nm(ecef_path.calculate_path_distances(ecef_points))
        self.assertEqual(len(distances), len(ecef_points))
        self.assertEqual(distances[0], 0.0)
        assert_almost_equal(distances[11], EXPECTED_PATH_DISTANCES[11], decimal=6)
        assert_array_almost_equal(distances, EXPECTED_PATH_DISTANCES)

    def test_EcefPath_find_index_and_ratio(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        # Start point
        index_0, ratio_0 = ecef_path.find_index_and_ratio(ecef_points[0])
        self.assertEqual(index_0, 0)
        self.assertEqual(ratio_0, 0.0)

        # Point at end of a straight leg
        pos_1 = ecef_points[1]
        index_1, ratio_1 = ecef_path.find_index_and_ratio(pos_1)
        self.assertEqual(index_1, 1)
        self.assertEqual(ratio_1, 0.0)

        # Point in middle of a straight leg
        pos_1_5 = ecef_path.calculate_position(1, 0.5)
        index_1_5, ratio_1_5 = ecef_path.find_index_and_ratio(pos_1_5)
        self.assertEqual(index_1_5, 1)
        assert_almost_equal(ratio_1_5, 0.5)

        # Point toward end of a turning leg
        pos_1_9 = ecef_path.calculate_position(1, 0.99)
        index_1_9, ratio_1_9 = ecef_path.find_index_and_ratio(pos_1_9)
        self.assertEqual(index_1_9, 1)
        assert_almost_equal(ratio_1_9, 0.99)

        # Point in middle of a turn
        pos_2 = ecef_path.calculate_position(2, 0.0)
        index_2, ratio_2 = ecef_path.find_index_and_ratio(pos_2)
        self.assertEqual(index_2, 2)
        assert_almost_equal(ratio_2, 0.0)

        # Point toward start of a turning leg
        pos_2_1 = ecef_path.calculate_position(2, 0.01)
        index_2_1, ratio_2_1 = ecef_path.find_index_and_ratio(pos_2_1)
        self.assertEqual(index_2_1, 2)
        assert_almost_equal(ratio_2_1, 0.01)

        # Point along a turning leg
        pos_2_25 = ecef_path.calculate_position(2, 0.25)
        index_2_25, ratio_2_25 = ecef_path.find_index_and_ratio(pos_2_25)
        self.assertEqual(index_2_25, 2)
        assert_almost_equal(ratio_2_25, 0.25)

        # Point in middle of a turning leg
        pos_2_5 = ecef_path.calculate_position(2, 0.5)
        index_2_5, ratio_2_5 = ecef_path.find_index_and_ratio(pos_2_5)
        self.assertEqual(index_2_5, 2)
        assert_almost_equal(ratio_2_5, 0.5)

        # Point along a turning leg
        pos_2_75 = ecef_path.calculate_position(2, 0.75)
        index_2_75, ratio_2_75 = ecef_path.find_index_and_ratio(pos_2_75)
        self.assertEqual(index_2_75, 2)
        assert_almost_equal(ratio_2_75, 0.75)

        # Finish point
        index_last, ratio_last = ecef_path.find_index_and_ratio(ecef_points[-1])
        self.assertEqual(index_last, 11)
        self.assertEqual(ratio_last, 0.0)

        # A waypoint not on path
        index_waypoint, ratio_waypoint = ecef_path.find_index_and_ratio(ecef_points[2])
        self.assertEqual(index_waypoint, 2)
        assert_almost_equal(ratio_waypoint, 0.0, decimal=6)

    def test_calculate_path_cross_track_distance(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        assert_almost_equal(ecef_path.calculate_path_cross_track_distance(ecef_points[0], 0), 0.0)
        assert_almost_equal(ecef_path.calculate_path_cross_track_distance(ecef_points[1], 1), 0.0)

        xtd_2_1 = ecef_path.calculate_path_cross_track_distance(ecef_points[2], 1)
        assert_almost_equal(rad2nm(xtd_2_1), 4.1416795658323213)

        xtd_2_2 = ecef_path.calculate_path_cross_track_distance(ecef_points[2], 2)
        assert_almost_equal(rad2nm(xtd_2_2), 4.1416795658323213)

        xtd_3_2 = ecef_path.calculate_path_cross_track_distance(ecef_points[3], 2)
        assert_almost_equal(rad2nm(xtd_3_2), 8.2824069920496726)

        xtd_3_3 = ecef_path.calculate_path_cross_track_distance(ecef_points[3], 3)
        assert_almost_equal(rad2nm(xtd_3_3), 8.2824069920496726)

    def test_EcefPath_calculate_cross_track_distances(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        distances = rad2nm(ecef_path.calculate_path_distances(ecef_points))
        self.assertEqual(len(distances), len(ecef_points))

        xtds = ecef_path.calculate_cross_track_distances(ecef_points, distances)
        self.assertEqual(len(xtds), len(ecef_points))
        assert_almost_equal(xtds[0], 0.0)
        assert_almost_equal(xtds[1], 0.0)
        assert_almost_equal(xtds[2], 4.1416795658323213)  # 10NM TID
        assert_almost_equal(xtds[3], 8.2824069920496726)  # 20NM TID
        assert_almost_equal(xtds[-1], 0.0)

    def test_EcefPath_section_distances_and_types(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        path_distances = rad2nm(ecef_path.path_distances())

        distances, types = ecef_path.section_distances_and_types()
        self.assertEqual(len(distances), len(ecef_path) + 8)
        self.assertEqual(len(types), len(ecef_path) + 8)

        self.assertEqual(distances[0], 0.0)
        self.assertEqual(types[0], PointType.Waypoint)

        self.assertEqual(distances[1], path_distances[1])
        self.assertEqual(types[1], PointType.Waypoint)

        self.assertTrue(distances[2] < path_distances[2])
        self.assertEqual(types[2], PointType.TurnStart)

        self.assertTrue(distances[3] > path_distances[2])
        self.assertEqual(types[3], PointType.TurnFinish)

        self.assertEqual(distances[-2], path_distances[-2])
        self.assertEqual(types[-2], PointType.Waypoint)

        self.assertEqual(distances[-1], path_distances[-1])
        self.assertEqual(types[-1], PointType.Waypoint)

    def test_EcefPath_calculate_positions(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        distances, types = ecef_path.section_distances_and_types()

        positions = ecef_path.calculate_positions(distances)
        self.assertEqual(len(positions), len(ecef_path) + 8)

        assert_array_almost_equal(positions[0], ecef_points[0])
        assert_array_almost_equal(positions[1], ecef_points[1])
        assert_array_almost_equal(positions[-2], ecef_points[-2])
        assert_array_almost_equal(positions[-1], ecef_points[-1])

    def test_EcefPath_calculate_ground_track(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        track_0 = ecef_path.calculate_ground_track(0, 0.0)
        assert_almost_equal(track_0, np.pi / 2, decimal=3)  # close to due East

        track_2_5 = ecef_path.calculate_ground_track(2, 0.5)
        assert_almost_equal(track_2_5, np.pi)  # due south

        track_2_0 = ecef_path.calculate_ground_track(2, 0.0)
        assert_almost_equal(track_2_0, 0.75 * np.pi, decimal=3)  # South East

        track_12_0 = ecef_path.calculate_ground_track(12, 0.0)
        assert_almost_equal(track_12_0, 0.0)  # North

    def test_EcefPath_calculate_ground_tracks(self):
        ecef_points = calculate_EcefPoints(ROUTE_LATS, ROUTE_LONS)

        ecef_path = EcefPath(ecef_points, TURN_DISTANCES)

        distances, types = ecef_path.section_distances_and_types()

        ground_tracks = ecef_path.calculate_ground_tracks(distances)
        self.assertEqual(len(ground_tracks), len(ecef_path) + 8)
        assert_almost_equal(ground_tracks[0], np.pi / 2, decimal=3)


if __name__ == '__main__':
    unittest.main()
