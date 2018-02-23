#!/usr/bin/env python
#
# Copyright (c) 2017-2018  Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
from numpy.testing import assert_almost_equal
from apps.convert_cpr_data import *


class TestConvertCprFunctions(unittest.TestCase):

    def test_cpr_date_parser(self):
        """Test conversion of CPR dates."""

        test_date1 = '20170204'
        result1 = cpr_date_parser(test_date1)

        self.assertEqual(result1.year, 2017)
        self.assertEqual(result1.month, 2)
        self.assertEqual(result1.day, 4)

        # invalid month
        test_date = '20170004'
        try:
            result2 = cpr_datetime_parser(test_date)
        except ValueError:
            self.assertTrue(True)

    def test_cpr_datetime_parser(self):
        """Test conversion of CPR date times."""

        test_datetime1 = '17/02/04 20:56:39'
        result1 = cpr_datetime_parser(test_datetime1)

        self.assertEqual(result1.year, 2017)
        self.assertEqual(result1.month, 2)
        self.assertEqual(result1.day, 4)

        self.assertEqual(result1.hour, 20)
        self.assertEqual(result1.minute, 56)
        self.assertEqual(result1.second, 39)

        # invalid hour
        test_datetime2 = '17/02/04 24:56:39'
        try:
            result2 = cpr_datetime_parser(test_datetime2)
        except ValueError:
            self.assertTrue(True)

    def test_cpr_latlong2decimal(self):
        """Test conversion of CPR Lat Long positions."""

        test_latlong1 = '540138S 0274539E'
        lat1, long1 = cpr_latlong2decimal(test_latlong1)
        assert_almost_equal(lat1, -54.02722222)
        assert_almost_equal(long1, 27.76083334)

        test_latlong1 = '480908N 0001922W'
        lat1, long1 = cpr_latlong2decimal(test_latlong1)
        assert_almost_equal(lat1, 48.1522222)
        assert_almost_equal(long1, -0.32277778)

    def test_cpr_track2decimal(self):
        """Test conversion of CPR track magentic field."""

        track1 = "234 07'27''"
        result1 = cpr_track2decimal(track1)
        assert_almost_equal(result1, 234.1241667)

        track2 = "031 58'13''"
        result2 = cpr_track2decimal(track2)
        assert_almost_equal(result2, 31.97027778)


if __name__ == '__main__':
    unittest.main()
