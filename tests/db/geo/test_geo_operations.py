#!/usr/bin/env python
#
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
import unittest
from pru.db.geo.geo_operations import merge_l_t, originates, make_point
from pru.db.geo.geo_operations import make_sector_description, find_airspace_by_database_ID
from pru.db.geo.geo_init import add_user_sector, add_airspace_geometry
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database, initialise_airspace
import pru.db.context as ctx
from os import environ as env

# THIS NEEDS TO BE SET ON THE ENVIRONMENT where you run the tests
# and must point to a directory where the test data files below can be found.
# ie export TEST_DATA_HOME=/path to test data files
TEST_DATA_HOME_ENV = 'TEST_DATA_HOME'

AIRSPACE_DATA_FILE = "ES_428.geojson"
AIRPORTS_DATA_FILE = "airports.csv"
MOVEMENTS_REPORTING_AIRPORTS_DATA_FILE = "movements_reporting_airports.csv"
FLEET_DATA_FILE = "fleet_data_2017-07-01.csv"
USER_DEFINED_AIRSPACES = "user_defined_airspaces.csv"


def make_test_data_file(file_name):
    def get_test_data_home():
        return env.get(TEST_DATA_HOME_ENV) + "/" + file_name
    return get_test_data_home


class Test_Remove_And_Add_Geo_Db(unittest.TestCase):
    """
    Test cases against the geo support operations of the airspace model.
    """

    def test_remove_db_then_create(self):
        """
        Completely remove the geo db and recreate
        """
        remove_geo_db()
        create_geo_database()

    def test_remove_db_then_create_and_initialise_sectors(self):
        """
        Completely remove the geo db and recreate
        """
        remove_geo_db()
        create_geo_database()
        make_airspace_file = make_test_data_file(AIRSPACE_DATA_FILE)
        initialise_airspace(make_airspace_file(), False)


class Test_Geo_Operations(unittest.TestCase):
    """
    Test cases against the geo support operations of the airspace model.
    """

    def test_mertge_l_t_single(self):
        """
        Test merge list of one tuple to list of lists.
        """
        sec_list = []
        lat_list = []
        lon_list = []
        packed_list = [lat_list, lon_list, sec_list]
        list_tuple_1 = [("a", 22, 33)]
        expected1 = [[22], [33], ["a"]]
        res1 = merge_l_t(packed_list, list_tuple_1)
        self.assertEqual(expected1, res1)

    def test_mertge_l_t_pair(self):
        """
        Test merge list of two tuples to list of lists.
        """
        sec_list = []
        lat_list = []
        lon_list = []
        packed_list = [lat_list, lon_list, sec_list]
        list_tuple_1 = [("a", 22, 33), ("a", 22.5, 33.5)]
        expected1 = [[22, 22.5], [33, 33.5], ["a", "a"]]
        res1 = merge_l_t(packed_list, list_tuple_1)
        self.assertEqual(expected1, res1)

    def test_mertge_l_t_empty(self):
        """
        Test merge list of empty tuples to list of lists.
        """
        sec_list = []
        lat_list = []
        lon_list = []
        packed_list = [lat_list, lon_list, sec_list]
        list_tuple_1 = []
        expected1 = [[], [], []]
        res1 = merge_l_t(packed_list, list_tuple_1)
        self.assertEqual(expected1, res1)


class Test_Originates(unittest.TestCase):
    """
    Test cases against originates function, two sectors stacked and one sector
    that is not the origin.
    """
    def simple_originates(self):

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        AC_ID = "991"
        AV_AIRSPACE_ID = "SQUARE_1_1"
        AV_ICAO_STATE_ID = "LZ"
        MIN_FLIGHT_LEVEL = "100"
        MAX_FLIGHT_LEVEL = "200"
        AV_NAME = "Square Sector Level 1"
        SECTOR_TYPE = "ES"
        OBJECT_ID = 2209999
        USER_SECTOR_1_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"

        # Upper layer of square sector
        AC_ID = "992"
        AV_AIRSPACE_ID_2 = "SQUARE_1_2"
        AV_ICAO_STATE_ID = "LZ"
        MIN_FLIGHT_LEVEL_2 = "200"
        MAX_FLIGHT_LEVEL_2 = "250"
        AV_NAME_2 = "Square Sector Level 2"
        SECTOR_TYPE = "ES"
        OBJECT_ID = 2209999
        USER_SECTOR_2_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"

        # Unrelated square sector
        AC_ID = "993"
        AV_AIRSPACE_ID_3 = "SQUARE_2_1"
        AV_ICAO_STATE_ID = "LZ"
        MIN_FLIGHT_LEVEL_2 = "200"
        MAX_FLIGHT_LEVEL_2 = "250"
        AV_NAME_3 = "Square Sector 2 Level 2"
        SECTOR_TYPE = "ES"
        OBJECT_ID = 2209999
        USER_SECTOR_3_WKT = "POLYGON ((-0.3 45.5, 0.3 45.5, 0.3 41.5, -0.3 41.5, -0.3 45.5))"

        FLIGHT_ID_1 = "west_to_east"
        ORIGIN_POINT = make_point(0.15, 50.0, connection)

        # A single sector as a square(ish)
        sector_1 = [AC_ID, AV_AIRSPACE_ID, AV_ICAO_STATE_ID, MIN_FLIGHT_LEVEL, MAX_FLIGHT_LEVEL, AV_NAME, SECTOR_TYPE, OBJECT_ID, USER_SECTOR_1_WKT]
        sector_2 = [AC_ID, AV_AIRSPACE_ID_2, AV_ICAO_STATE_ID, MIN_FLIGHT_LEVEL_2, MAX_FLIGHT_LEVEL_2, AV_NAME_2, SECTOR_TYPE, OBJECT_ID, USER_SECTOR_2_WKT]
        sector_3 = [AC_ID, AV_AIRSPACE_ID_3, AV_ICAO_STATE_ID, MIN_FLIGHT_LEVEL_2, MAX_FLIGHT_LEVEL_2, AV_NAME_3, SECTOR_TYPE, OBJECT_ID, USER_SECTOR_3_WKT]

        # Add to the sectors database
        ok, sector_1_id = add_airspace_geometry(sector_1, context, connection)
        self.assertTrue(ok)
        ok, sector_2_id = add_airspace_geometry(sector_2, context, connection)
        self.assertTrue(ok)
        ok, sector_3_id = add_airspace_geometry(sector_3, context, connection)
        self.assertTrue(ok)

        self.assertTrue(originates(ORIGIN_POINT, USER_SECTOR_1_WKT, FLIGHT_ID_1, sector_1_id, connection))
        self.assertTrue(originates(ORIGIN_POINT, USER_SECTOR_2_WKT, FLIGHT_ID_1, sector_2_id, connection))
        self.assertFalse(originates(ORIGIN_POINT, USER_SECTOR_3_WKT, FLIGHT_ID_1, sector_3_id, connection))


class TestMakeSectorDescription(unittest.TestCase):
    """

    """
    USER_DEFINED_INTERSECTION_1 = {'org_id': 'user org', 'user_id': 'user one', 'sector_name': 'sector one'}
    USER_DEFINED_BLANK_ORG_2 = {'org_id': '', 'user_id': 'user one', 'sector_name': 'sector two'}
    USER_DEFINED_NONE_ORG_3 = {'org_id': None, 'user_id': 'user one', 'sector_name': 'sector two'}

    INTERSECTION_1 = {'av_icao_state_id': 'user org', 'av_name': 'one', 'id': '1', 'av_airspace_id': 'av_1'}
    BLANK_AV_ICAO_STATE_ID = {'av_icao_state_id': '', 'av_name': 'two', 'id': '2', 'av_airspace_id': 'av_2'}
    NONE_AV_ICAO_STATE_ID = {'av_icao_state_id': None, 'av_name': 'three', 'id': '3', 'av_airspace_id': 'av_3'}

    def test_make_simple_user_description(self):
        description_1 = make_sector_description(self.USER_DEFINED_INTERSECTION_1, True)
        self.assertTrue(description_1)
        description_2 = make_sector_description(self.USER_DEFINED_BLANK_ORG_2, True)
        self.assertTrue(description_2)
        description_3 = make_sector_description(self.USER_DEFINED_NONE_ORG_3, True)
        self.assertTrue(description_3)

    def test_make_simple_description(self):
        description_1 = make_sector_description(self.INTERSECTION_1, False)
        self.assertTrue(description_1)
        description_2 = make_sector_description(self.BLANK_AV_ICAO_STATE_ID, False)
        self.assertTrue(description_2)
        description_3 = make_sector_description(self.NONE_AV_ICAO_STATE_ID, False)
        self.assertTrue(description_3)


class TestMakePoint(unittest.TestCase):
    """

    """

    LAT_1 = 0.0
    LON_1 = 0.0
    LAT_2 = 50.0
    LON_2 = 10.0
    LAT_3 = -50.0
    LON_3 = -10.0
    LAT_4 = -100.0
    LON_4 = -370.0
    LAT_5 = 200.0
    LON_5 = 370.0

    def test_make_simple_point(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        self.assertTrue(make_point(self.LON_1, self.LAT_1, connection))
        self.assertTrue(make_point(self.LON_2, self.LAT_2, connection))
        self.assertTrue(make_point(self.LON_3, self.LAT_3, connection))
        self.assertTrue(make_point(self.LON_4, self.LAT_4, connection))
        self.assertTrue(make_point(self.LON_5, self.LAT_5, connection))


class TestMakeAugmentedPoint(unittest.TestCase):
    LAT_1 = 0.0
    LON_1 = 0.0
    POSITION_1 = (LAT_1, LON_1)
    LAT_2 = 50.0
    LON_2 = 10.0
    POSITION_1 = (LAT_2, LON_2)
    LAT_3 = -50.0
    LON_3 = -10.0
    POSITION_1 = (LAT_3, LON_3)
    LAT_4 = -100.0
    LON_4 = -370.0
    POSITION_1 = (LAT_3, LON_3)


class TestFindAirspaceByDBId(unittest.TestCase):

    AC_ID = "991"
    AV_AIRSPACE_ID = "SQUARE_1_1"
    AV_ICAO_STATE_ID = "LZ"
    MIN_FLIGHT_LEVEL = "100"
    MAX_FLIGHT_LEVEL = "200"
    AV_NAME = "Square Sector Level 1"
    SECTOR_TYPE = "ES"
    OBJECT_ID = 2209999
    USER_SECTOR_1_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"

    ORG_ID = "MY ORG"
    USER_ID = "Tester 1"
    SECTOR_NAME = "User Square Sector Level 1"
    SECTOR_NAME_2 = "User Square Sector Level 2"
    USER_MIN_FLIGHT_LEVEL = "100"
    USER_MAX_FLIGHT_LEVEL = "200"
    LAT = 50.0
    LON = 22.0
    RAD = 20.0
    USER_SECTOR_1_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"

    def test_find_by_id(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        sector_1 = [self.AC_ID, self.AV_AIRSPACE_ID, self.AV_ICAO_STATE_ID,
                    self.MIN_FLIGHT_LEVEL, self.MAX_FLIGHT_LEVEL, self.AV_NAME,
                    self.SECTOR_TYPE, self.OBJECT_ID, self.USER_SECTOR_1_WKT]
        ok, sector_1_id = add_airspace_geometry(sector_1, context, connection)
        self.assertTrue(ok)
        res = find_airspace_by_database_ID(sector_1_id, context, connection, is_user_defined=False)
        self.assertEquals(1, len(res))
        sector = res[0]
        self.assertEquals(11, len(sector))

        user_sector_1 = [self.ORG_ID, self.USER_ID, self.SECTOR_NAME, self.LAT,
                         self.LON, self.RAD, self.USER_MIN_FLIGHT_LEVEL,
                         self.USER_MAX_FLIGHT_LEVEL, False, self.USER_SECTOR_1_WKT]
        ok, user_sector_1_id = add_user_sector(user_sector_1, context, connection)
        self.assertTrue(ok)
        res = find_airspace_by_database_ID(user_sector_1_id, context, connection, is_user_defined=True)
        self.assertEquals(1, len(res))
        user_sector = res[0]
        self.assertEquals(12, len(user_sector))
        self.assertEquals(self.ORG_ID, user_sector['org_id'])
        self.assertEquals(self.USER_ID, user_sector['user_id'])
        self.assertEquals(self.SECTOR_NAME, user_sector['sector_name'])
        self.assertEquals(int(self.USER_MIN_FLIGHT_LEVEL) * 100, user_sector['min_altitude'])

        user_sector_2 = [self.ORG_ID, self.USER_ID, self.SECTOR_NAME_2, self.LAT,
                         self.LON, self.RAD, self.USER_MIN_FLIGHT_LEVEL,
                         self.USER_MAX_FLIGHT_LEVEL, True, self.USER_SECTOR_1_WKT]
        ok, user_sector_2_id = add_user_sector(user_sector_2, context, connection)
        self.assertTrue(ok)
        res = find_airspace_by_database_ID(user_sector_2_id, context, connection, is_user_defined=True)
        self.assertEquals(1, len(res))
        user_sector_2 = res[0]
        self.assertEquals(12, len(user_sector))
        self.assertEquals(self.ORG_ID, user_sector_2['org_id'])
        self.assertEquals(self.USER_ID, user_sector_2['user_id'])
        self.assertEquals(self.SECTOR_NAME_2, user_sector_2['sector_name'])
        self.assertEquals(int(self.USER_MIN_FLIGHT_LEVEL) * 100, user_sector_2['min_altitude'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(Test_Geo_Operations('test_mertge_l_t_single'))
    suite.addTest(Test_Geo_Operations('test_mertge_l_t_pair'))
    suite.addTest(Test_Geo_Operations('test_mertge_l_t_empty'))

    # Need an empty sector table here
    suite.addTest(Test_Remove_And_Add_Geo_Db('test_remove_db_then_create'))

    suite.addTest(Test_Originates('simple_originates'))

    suite.addTest(TestMakeSectorDescription('test_make_simple_user_description'))
    suite.addTest(TestMakeSectorDescription('test_make_simple_description'))
    suite.addTest(TestMakePoint('test_make_simple_point'))
    suite.addTest(TestFindAirspaceByDBId('test_find_by_id'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
