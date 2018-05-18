#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
import numpy as np
import json
from numpy.testing import assert_array_almost_equal
from pru.HorizontalPath import HorizontalPath
from pru.TimeProfile import TimeProfile
from pru.AltitudeProfile import AltitudeProfile
from pru.SmoothedTrajectory import SmoothedTrajectory, \
    dumps_SmoothedTrajectories, loads_SmoothedTrajectories

GOLDEN_ANGLE = np.rad2deg(np.arctan(2.0))
LATITUDE = 90.0 - GOLDEN_ANGLE

NM = np.deg2rad(1.0 / 60.0)

ROUTE_LATS = np.array([90.0, LATITUDE, LATITUDE,
                       LATITUDE, LATITUDE, LATITUDE,
                       -LATITUDE, -LATITUDE, -LATITUDE,
                       -LATITUDE, -LATITUDE, -90.0])
ROUTE_LONS = np.array([0.0, 180.0, -1.5 * 72.0,
                       -0.5 * 72.0, 0.5 * 72.0, 1.5 * 72.0,
                       2.0 * 72.0, -2.0 * 72.0, -1.0 * 72.0,
                       0.0, 1.0 * 72.0, 0.0])
""" An Icosahedron with vertices at the North and South poles. """

TURN_DISTANCES = np.array([0., 0., 10 * NM,
                           20 * NM, 20 * NM, 20 * NM,
                           20 * NM, 20 * NM, 20 * NM,
                           20 * NM, 0., 0.])

START_TIME = np.datetime64('2017-08-01T08:47:31.000')

ELAPSED_TIMES = np.array([0.,   292.,   718.,
                          2543.,  2573.,  2603.,
                          2633.,  2663.,  2693.,
                          2723.,  2753.,  2759.])

TIME_DISTANCES = np.array([0., 5 * NM, 10 * NM,
                           15 * NM, 20 * NM, 25 * NM,
                           30 * NM, 35 * NM, 40 * NM,
                           45 * NM, 50 * NM, 55 * NM])

ALTITUDES = np.array([0., 1800., 3000.,
                      3600., 4200., 4800.,
                      5400., 6000., 6000.,
                      6000., 6000.0, 5400.])
ALT_DISTANCES = np.array([0., 5 * NM, 10 * NM,
                          15 * NM, 20 * NM, 25 * NM,
                          30 * NM, 35 * NM, 40 * NM,
                          45 * NM, 50 * NM, 55 * NM])


class TestSmoothedTrajectory(unittest.TestCase):

    def test_SmoothedTrajectory(self):
        path_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)
        timep_0 = TimeProfile(START_TIME, TIME_DISTANCES, ELAPSED_TIMES)
        altp_0 = AltitudeProfile(ALT_DISTANCES, ALTITUDES)

        traj_0 = SmoothedTrajectory('123-456-789', path_0, timep_0, altp_0)
        s = traj_0.dumps()

        # print(s)
        json_1 = json.loads(s)
        traj_1 = SmoothedTrajectory.loads(json_1)

        self.assertEqual(traj_1.flight_id, '123-456-789')
        assert_array_almost_equal(traj_1.path.lats, ROUTE_LATS)
        assert_array_almost_equal(traj_1.path.lons, ROUTE_LONS)
        assert_array_almost_equal(traj_1.path.tids, TURN_DISTANCES)

        self.assertEqual(traj_1.timep.start_time, START_TIME)
        assert_array_almost_equal(traj_1.timep.distances, TIME_DISTANCES)
        assert_array_almost_equal(traj_1.timep.elapsed_times, ELAPSED_TIMES)

        assert_array_almost_equal(traj_1.altp.distances, ALT_DISTANCES)
        assert_array_almost_equal(traj_1.altp.altitudes, ALTITUDES)

    def test_SmoothedTrajectories(self):
        path_0 = HorizontalPath(ROUTE_LATS, ROUTE_LONS, TURN_DISTANCES)
        timep_0 = TimeProfile(START_TIME, TIME_DISTANCES, ELAPSED_TIMES)
        altp_0 = AltitudeProfile(ALT_DISTANCES, ALTITUDES)

        traj_0 = SmoothedTrajectory('123-456-789', path_0, timep_0, altp_0)

        trajs_0 = [traj_0, traj_0, traj_0]

        s = dumps_SmoothedTrajectories(trajs_0, 'lm', 0.5)
        # print(s)

        json_1 = json.loads(s)
        trajs_1 = loads_SmoothedTrajectories(json_1)
        self.assertEqual(len(trajs_1), len(trajs_0))


if __name__ == '__main__':
    unittest.main()
