#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import pandas as pd
from numpy.testing import assert_almost_equal, assert_array_almost_equal
from os import environ as env
from pru.trajectory_cleaning import *

TEST_DATA_HOME = 'TEST_DATA_HOME'


class TestTrajectoryCleaning(unittest.TestCase):

    def test_find_invalid_positions_1(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        # BAW307 has an invalid position with the same SSR code but a
        # different aircraft address
        filename_1 = '/cpr_259599_BAW307_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename_1,
                                parse_dates=['TIME'])

        # Test position search
        invalid_pos0, metrics0 = find_invalid_positions(points_df,
                                                        find_invalid_addresses=False)
        self.assertEqual(metrics0[ErrorCounts.TOTAL], 1)
        self.assertEqual(metrics0[ErrorCounts.DUPLICATE_POSITIONS], 0)
        self.assertEqual(metrics0[ErrorCounts.INVALID_ADDRESSES], 0)
        self.assertEqual(metrics0[ErrorCounts.INVALID_POSITIONS], 1)
        self.assertEqual(metrics0[ErrorCounts.INVALID_ALTITUDES], 0)

        # Test invalid addresses search
        invalid_pos1, metrics1 = find_invalid_positions(points_df,
                                                        find_invalid_addresses=True)
        assert_array_almost_equal(invalid_pos0, invalid_pos1)
        self.assertEqual(metrics1[ErrorCounts.TOTAL], 1)
        self.assertEqual(metrics1[ErrorCounts.DUPLICATE_POSITIONS], 0)
        self.assertEqual(metrics1[ErrorCounts.INVALID_ADDRESSES], 1)
        self.assertEqual(metrics1[ErrorCounts.INVALID_POSITIONS], 0)
        self.assertEqual(metrics1[ErrorCounts.INVALID_ALTITUDES], 0)

    def test_find_invalid_positions_2(self):
        test_data_home = env.get('TEST_DATA_HOME')
        self.assertTrue(test_data_home)

        # SAS1643 has two invalid positions: a duplicates at a different altitude
        # with different SSR codes and aircraft addresses
        filename_1 = '/cpr_255332_SAS1643_2017-08-01.csv'
        points_df = pd.read_csv(test_data_home + filename_1,
                                parse_dates=['TIME'])

        # Test position search
        invalid_pos0, metrics0 = find_invalid_positions(points_df,
                                                        find_invalid_addresses=False)
        self.assertEqual(metrics0[ErrorCounts.TOTAL], 2)
        self.assertEqual(metrics0[ErrorCounts.DUPLICATE_POSITIONS], 1)
        self.assertEqual(metrics0[ErrorCounts.INVALID_ADDRESSES], 0)
        self.assertEqual(metrics0[ErrorCounts.INVALID_POSITIONS], 0)
        self.assertEqual(metrics0[ErrorCounts.INVALID_ALTITUDES], 1)

        # Test invalid addresses search
        invalid_pos1, metrics1 = find_invalid_positions(points_df,
                                                        find_invalid_addresses=True)
        assert_array_almost_equal(invalid_pos0, invalid_pos1)
        self.assertEqual(metrics1[ErrorCounts.TOTAL], 2)
        self.assertEqual(metrics1[ErrorCounts.DUPLICATE_POSITIONS], 1)
        self.assertEqual(metrics1[ErrorCounts.INVALID_ADDRESSES], 2)
        self.assertEqual(metrics1[ErrorCounts.INVALID_POSITIONS], 0)
        self.assertEqual(metrics1[ErrorCounts.INVALID_ALTITUDES], 0)


if __name__ == '__main__':
    unittest.main()
