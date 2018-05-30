#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest

from pru.AirspaceVolume import AirspaceVolume


class TestAirspaceVolume(unittest.TestCase):

    def test_vertical_intersections(self):
        test_vol = AirspaceVolume('test1', 10000, 20000)

        self.assertEqual(test_vol.name, 'test1')
        self.assertEqual(test_vol.bottom_altitude, 10000)
        self.assertEqual(test_vol.top_altitude, 20000)

        self.assertFalse(test_vol.is_inside(9999))
        # Equals bottom level, so True
        self.assertTrue(test_vol.is_inside(10000))

        self.assertTrue(test_vol.is_inside(19999))
        self.assertFalse(test_vol.is_inside(20000))

        self.assertFalse(test_vol.vertical_intersection(9000, 9999))
        # Equals bottom level, so True
        self.assertTrue(test_vol.vertical_intersection(10000, 11000))

        self.assertTrue(test_vol.vertical_intersection(19999, 21000))
        self.assertFalse(test_vol.vertical_intersection(20000, 21000))

        # Spans bottom level, so True
        self.assertTrue(test_vol.bottom_intersection(9000, 11000))

        # Equal to bottom level so False, no vertical intersection
        self.assertFalse(test_vol.bottom_intersection(9000, 10000))
        self.assertFalse(test_vol.bottom_intersection(10000, 11000))

        # Spans top level, so True
        self.assertTrue(test_vol.top_intersection(19000, 21000))

        # Equal to top level so False, no vertical intersection
        self.assertFalse(test_vol.top_intersection(19000, 20000))
        self.assertFalse(test_vol.top_intersection(20000, 21000))

    def test_id_name_conversion(self):
        test_vol1 = AirspaceVolume('test1', 10000, 20000)
        test_vol2 = AirspaceVolume('test2', 10000, 20000)
        test_vol3 = AirspaceVolume('test3', 10000, 20000)

        volumes = {'1': test_vol1,
                   '2': test_vol2,
                   '3': test_vol3}

        volume_ids = ['2', '1', '3', '1']
        volume_names = [volumes.get(item).name for item in volume_ids]

        self.assertEqual(volume_names[0], 'test2')
        self.assertEqual(volume_names[1], 'test1')
        self.assertEqual(volume_names[2], 'test3')
        self.assertEqual(volume_names[-1], 'test1')


if __name__ == '__main__':
    unittest.main()
