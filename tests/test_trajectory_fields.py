#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
from numpy.testing import assert_almost_equal
from pru.trajectory_fields import *


class TestConvertADSBFunctions(unittest.TestCase):

    def test_dms2decimal(self):
        """Test conversion of degrees minutes and seconds."""

        result1 = dms2decimal(45, 30, 0, True)
        self.assertEqual(result1, -45.5)

        result2 = dms2decimal(89, 59, 59)
        assert_almost_equal(result2, 89.9997222)

    def test_iso8601_date_parser(self):
        """Test conversion of ADS-B date times."""

        test_date1 = '2017-08-01'
        result1 = iso8601_date_parser(test_date1)

        self.assertEqual(result1.year, 2017)
        self.assertEqual(result1.month, 8)
        self.assertEqual(result1.day, 1)

        # invalid month
        test_date2 = '2017-13-01'
        try:
            result2 = iso8601_date_parser(test_date2)
        except ValueError:
            self.assertTrue(True)

    def test_is_valid_iso8601_date(self):
        """Test validation of ADS-B date times."""

        test_date1 = '2017-08-01'
        self.assertTrue(is_valid_iso8601_date(test_date1))

        # invalid month
        test_date2 = '2017-13-01'
        self.assertFalse(is_valid_iso8601_date(test_date2))

    def test_iso8601_datetime_parser(self):
        """Test conversion of ADS-B date times."""

        test_datetime1 = '2017-08-01T01:37:21Z'
        result1 = iso8601_datetime_parser(test_datetime1)

        self.assertEqual(result1.year, 2017)
        self.assertEqual(result1.month, 8)
        self.assertEqual(result1.day, 1)

        self.assertEqual(result1.hour, 1)
        self.assertEqual(result1.minute, 37)
        self.assertEqual(result1.second, 21)

        # invalid hour
        test_datetime2 = '2017-08-01T24:37:21Z'
        try:
            result2 = iso8601_datetime_parser(test_datetime2)
        except ValueError:
            self.assertTrue(True)

        # invalid letter in place of Z
        test_datetime3 = '2017-08-01T01:37:21X'
        try:
            result3 = iso8601_datetime_parser(test_datetime3)
        except ValueError:
            self.assertTrue(True)

    def test_has_bz2_extension(self):

        test_filename1 = 'FR24_ADSB_DATA_FLIGHTS_2017-08-01.csv.bz2'
        self.assertTrue(has_bz2_extension(test_filename1))

        test_filename2 = 'FR24_ADSB_DATA_FLIGHTS_2017-08-01.csv'
        self.assertFalse(has_bz2_extension(test_filename2))

    def test_read_iso8601_date_string(self):

        test_filename1 = 'FR24_ADSB_DATA_FLIGHTS_2017-08-01.csv.bz2'
        date1 = read_iso8601_date_string(test_filename1)
        self.assertEqual(date1, '2017-08-01')

        test_filename2 = 'FR24_ADSB_DATA_FLIGHTS_2017-08-01.csv'
        date2 = read_iso8601_date_string(test_filename2)
        self.assertEqual(date2, '2017-08-01')

        test_filename3 = 'trajectories_2017-08-01.json'
        date3 = read_iso8601_date_string(test_filename3, is_json=True)
        self.assertEqual(date3, '2017-08-01')

    def test_create_iso8601_csv_filename(self):

        test_name = 'fr24_positions_'
        test_date = '2017-08-01'
        test_filename1 = create_iso8601_csv_filename(test_name, test_date)
        self.assertEqual(test_filename1, 'fr24_positions_2017-08-01.csv')

        test_filename2 = create_iso8601_csv_filename(test_name, test_date, is_bz2=True)
        self.assertEqual(test_filename2, 'fr24_positions_2017-08-01.csv.bz2')


if __name__ == '__main__':
    unittest.main()
