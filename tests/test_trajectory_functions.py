#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from pru.trajectory_functions import *


class TestTrajectoryFunctions(unittest.TestCase):

    def test_calculate_delta_time(self):
        start_time = np.datetime64('2017-08-01 11:15')
        finish_time = np.datetime64('2017-08-01 11:16')
        self.assertEqual(calculate_delta_time(start_time, finish_time), 60.0)

    def test_calculate_elapsed_times(self):
        start_time = np.datetime64('2017-08-01 11:15')
        finish_time = np.datetime64('2017-08-01 11:15:30')
        date_times = np.arange(start_time, finish_time, np.timedelta64(5, 's'))

        expected_times = [0, 5, 10, 15, 20, 25]
        times = calculate_elapsed_times(date_times, date_times[0])
        self.assertEqual(len(times), len(expected_times))
        assert_array_almost_equal(times, expected_times)

    def test_calculate_date_times(self):
        start_time = np.datetime64('2017-08-01 11:15')
        elapsed_times = np.array([0.0, 5.1, 10.2, 15.3, 20.4, 25.456789])
        date_times = calculate_date_times(elapsed_times, start_time)
        self.assertEqual(len(date_times), len(elapsed_times))
        self.assertEqual(date_times[0], start_time)

        finish_time = np.datetime64('2017-08-01 11:15:25.456789')
        self.assertEqual(date_times[-1], finish_time)

    def test_calculate_leg_durations(self):
        """Test the calculate_leg_durations function."""
        start_time = np.datetime64('2017-08-01 11:15')
        finish_time = np.datetime64('2017-08-01 11:16')
        datetimes = np.arange(start_time, finish_time, np.timedelta64(5, 's'))

        durations = calculate_leg_durations(datetimes)
        self.assertEqual(len(durations), len(datetimes))

        self.assertEqual(durations[0], 0.0)
        for i in range(1, len(datetimes)):
            self.assertEqual(durations[i], 5.0)

    def test_calculate_speed(self):
        speed1 = calculate_speed(1.0, 1.0)
        assert_almost_equal(speed1, 3600.0)

        speed2 = calculate_speed(1.0, 2.0)
        assert_almost_equal(speed2, 1800.0)

        speed3 = calculate_speed(1.0, 3.0)
        assert_almost_equal(speed3, 1200.0)

        speed3 = calculate_speed(1.0, 0.0)
        assert_almost_equal(speed3, 7200.0)

        speed3 = calculate_speed(1.0, 0.0, min_time=1.0)
        assert_almost_equal(speed3, 3600.0)

    def test_calculate_min_speed(self):
        DISTANCE_ACCURACY = 0.25
        TIME_PRECISION = 1.0
        speed0 = calculate_min_speed(0.0, 0.0, DISTANCE_ACCURACY, TIME_PRECISION)
        assert_almost_equal(speed0, -900.0)

        speed025 = calculate_min_speed(DISTANCE_ACCURACY, 0.0,
                                       DISTANCE_ACCURACY, TIME_PRECISION)
        assert_almost_equal(speed025, 0.0)

        speed1 = calculate_min_speed(1.0, 1.0, DISTANCE_ACCURACY, TIME_PRECISION)
        assert_almost_equal(speed1, 1350.0)

        speed2 = calculate_min_speed(1.0, 2.0, DISTANCE_ACCURACY, TIME_PRECISION)
        assert_almost_equal(speed2, 900.0)

        speed3 = calculate_min_speed(1.0, 3.0, DISTANCE_ACCURACY, TIME_PRECISION)
        assert_almost_equal(speed3, 675.0)

    def test_find_duplicate_values(self):

        distances = np.array(range(10))
        dups_0 = find_duplicate_values(distances, 0.25)
        self.assertFalse(dups_0.any())

        distances[6] = distances[5]
        dups_1 = find_duplicate_values(distances, 0.25)
        self.assertTrue(dups_1.any())

    def test_max_delta(self):

        deltas = np.zeros(10, dtype=float)
        self.assertEqual(max_delta(deltas), 0.0)

        deltas[3] = 1.0
        self.assertEqual(max_delta(deltas), 1.0)

        deltas[5] = -2.0
        self.assertEqual(max_delta(deltas), 2.0)

    def test_calculate_altitude_differences(self):
        """Test the calculate_altitude_differences function."""
        altitudes = np.array([10000 - 100 * i for i in range(10)],
                             dtype=float)

        delta_alts = calculate_altitude_differences(altitudes)
        self.assertEqual(len(delta_alts), len(altitudes))

        self.assertEqual(delta_alts[0], 0.0)
        for i in range(1, len(delta_alts)):
            self.assertEqual(delta_alts[i], -100.0)

    def test_calculate_vertical_speed(self):
        speed1 = calculate_vertical_speed(100, 1.0)
        assert_almost_equal(speed1, 6000.0)

        speed2 = calculate_vertical_speed(100, 2.0)
        assert_almost_equal(speed2, 3000.0)

        speed3 = calculate_vertical_speed(100, 3.0)
        assert_almost_equal(speed3, 2000.0)

        speed1 = calculate_vertical_speed(100, 0.0)
        assert_almost_equal(speed1, 12000.0)

        speed1 = calculate_vertical_speed(100, 0.0, min_time=1.0)
        assert_almost_equal(speed1, 6000.0)

    def test_convert_angle_to_track_angle(self):

        ANGLES_RADS = np.array([0., np.pi, 2.0 * np.pi,
                                -np.pi, -0.5 * np.pi, -2.0 * np.pi])

        TRACKS_DEGS = np.array([0., 180., 360.0,
                                180.0, 270.0, 0.0])

        results = convert_angle_to_track_angle(ANGLES_RADS)
        assert_array_almost_equal(results, TRACKS_DEGS)

    def test_calculate_common_period(self):
        """Test the calculate_common_period function."""
        datetimes_1 = np.arange(np.datetime64('2017-08-01 11:15'),
                                np.datetime64('2017-08-01 11:25'),
                                np.timedelta64(5, 's'))

        datetimes_2 = np.arange(np.datetime64('2017-08-01 11:20'),
                                np.datetime64('2017-08-01 11:30'),
                                np.timedelta64(5, 's'))

        start_time = datetimes_2[0]
        finish_time = datetimes_1[-1]

        start_1, finish_1 = calculate_common_period(datetimes_1, datetimes_2)
        self.assertEqual(start_1, start_time)
        self.assertEqual(finish_1, finish_time)

        # test opposite order
        start_2, finish_2 = calculate_common_period(datetimes_2, datetimes_1)
        self.assertEqual(start_2, start_time)
        self.assertEqual(finish_2, finish_time)

    def test_calculate_value_reference_time(self):
        """Test the calculate_value_reference function with a time series."""
        start_time = np.datetime64('2017-08-01 11:15')
        datetimes = np.arange(start_time, np.datetime64('2017-08-01 11:25'),
                              np.timedelta64(5, 's'))

        start_time = datetimes[0]
        finish_time = datetimes[-1]

        # use the first value
        index_1, ratio_1 = calculate_value_reference(datetimes, start_time,
                                                     is_time=True)
        self.assertEqual(index_1, 0)
        self.assertEqual(ratio_1, 0.0)

        # use the last value
        index_2, ratio_2 = calculate_value_reference(datetimes, finish_time,
                                                     is_time=True)
        self.assertEqual(index_2, len(datetimes) - 1)
        self.assertEqual(ratio_2, 0.0)

        index_3, ratio_3 = calculate_value_reference(datetimes, datetimes[17],
                                                     is_time=True)
        self.assertEqual(index_3, 17)
        self.assertEqual(ratio_3, 0.0)

        time_4 = start_time + np.timedelta64(3, 's')
        index_4, ratio_4 = calculate_value_reference(datetimes, time_4, is_time=True)
        self.assertEqual(index_4, 0)
        self.assertEqual(ratio_4, 0.6)

        time_5 = start_time + np.timedelta64(7, 's')
        index_5, ratio_5 = calculate_value_reference(datetimes, time_5, is_time=True)
        self.assertEqual(index_5, 1)
        self.assertEqual(ratio_5, 0.4)

        time_6 = start_time + np.timedelta64(149, 's')
        index_6, ratio_6 = calculate_value_reference(datetimes, time_6, is_time=True)
        self.assertEqual(index_6, 29)
        self.assertEqual(ratio_6, 0.8)

    def test_calculate_value(self):
        """Test the calculate_value function with an altitude series."""
        alts = np.array([20 + i for i in range(10)], dtype=float)
        alts *= 100

        self.assertEqual(calculate_value(alts, 0), 2000.0)
        self.assertEqual(calculate_value(alts, 5), 2500.0)
        self.assertEqual(calculate_value(alts, 5, 0.5), 2550.0)
        self.assertEqual(calculate_value(alts, 9, 0.5), 2900.0)
        self.assertEqual(calculate_value(alts, 10, 0.0), 2900.0)

    def test_compare_trajectory_positions(self):
        """Test the compare_trajectory_positions function."""
        datetimes_1 = np.arange(np.datetime64('2017-08-01 11:15'),
                                np.datetime64('2017-08-01 11:25'),
                                np.timedelta64(1, 'm'))

        datetimes_2 = np.arange(np.datetime64('2017-08-01 11:20'),
                                np.datetime64('2017-08-01 11:30'),
                                np.timedelta64(1, 'm'))

        datetimes_3 = np.arange(np.datetime64('2017-08-01 11:24'),
                                np.datetime64('2017-08-01 11:34'),
                                np.timedelta64(1, 'm'))

        datetimes_4 = np.arange(np.datetime64('2017-08-01 11:25'),
                                np.datetime64('2017-08-01 11:35'),
                                np.timedelta64(1, 'm'))

        LATITUDES = np.zeros(len(datetimes_1), dtype=float)
        LONGITUDES_1 = np.array([-5 + i for i in range(len(datetimes_1))], dtype=float)
        ecef_points_1 = calculate_EcefPoints(LATITUDES, LONGITUDES_1)

        values1 = np.zeros(len(datetimes_1), dtype=float)

        alts1 = np.full(len(datetimes_1), 21000.0, dtype=float)
        alts2 = np.full(len(datetimes_1), 22000.0, dtype=float)

        # Identical trajectories
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                     ecef_points_1, ecef_points_1,
                                                     alts1, alts1))

        # Different altitudes
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts2))

        # Different altitudes, within alt_threshold
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_1,
                                                     ecef_points_1, ecef_points_1,
                                                     alts1, alts2, alt_threshold=1000.0))

        # Second trajectory delayed by 5 mins
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_2,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts1))

        # Second trajectory delayed by 10 mins
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_3,
                                                      ecef_points_1, ecef_points_1,
                                                      alts1, alts1))

        LONGITUDES_2 = np.array([i for i in range(len(datetimes_2))], dtype=float)
        ecef_points_2 = calculate_EcefPoints(LATITUDES, LONGITUDES_2)

        # Second trajectory delayed by 5 mins, by first trajectory
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_2,
                                                     ecef_points_1, ecef_points_2,
                                                     alts1, alts1))

        LONGITUDES_3 = np.array([4 + i for i in range(len(datetimes_3))], dtype=float)
        ecef_points_3 = calculate_EcefPoints(LATITUDES, LONGITUDES_3)

        # Second trajectory delayed by 9 mins, by end of first trajectory
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_3,
                                                     ecef_points_1, ecef_points_3,
                                                     alts1, alts1))

        # Second trajectory delayed by 10 mins, by end of first trajectory
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                      ecef_points_1, ecef_points_3,
                                                      alts1, alts1))

        # Second trajectory delayed by 10 mins, by end of first trajectory
        # with a minutes time_threshold.
        self.assertTrue(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                     ecef_points_3, ecef_points_1,
                                                     alts1, alts1, time_threshold=60.0,
                                                     speed_threshold=750.0))

        # But other way around, ends are not close enough
        self.assertFalse(compare_trajectory_positions(datetimes_1, datetimes_4,
                                                      ecef_points_1, ecef_points_3,
                                                      alts1, alts1, time_threshold=60.0,
                                                      speed_threshold=750.0))

    def test_set_exit_flags(self):
        """Test the set_exit_flags function."""
        ids_1 = ['A', 'A', 'B', 'C', 'C', 'C', 'A', 'A', 'A', 'A']
        exits = np.array([False, True, False, False, True, False, False, True, False, True])

        result = set_exit_flags(ids_1)
        assert_array_almost_equal(result, exits)
        # print(exits.tolist())
        # self.assertFalse(exits[0])


if __name__ == '__main__':
    unittest.main()
