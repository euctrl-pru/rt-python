#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Test geo init operations.
Run using tests/db/geo/test_geo_init.py
"""
import unittest
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database
from pru.db.geo.geo_init import load_user_airspace, load_airports, load_airspace
from pru.db.geo.geo_init import create_GIST_index
import pru.db.context as ctx
from psycopg2.extensions import AsIs
from psycopg2.extras import DictCursor
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
    """
    Used to get the datafile paths eg :
    get_airspace_file_path = make_test_data_file(AIRSPACE_DATA_FILE)
    path_string = get_airspace_file_path()
    """
    def get_test_data_home():
        return env.get(TEST_DATA_HOME_ENV) + "/" + file_name
    return get_test_data_home


class Test_Geo_Operations(unittest.TestCase):
    """
    Test cases against the geo support operations of the airspace model.
    """

    def test_remove_db_then_create_and_initialise_sectors(self):
        """
        Completely remove the geo db and recreate
        """
        remove_geo_db()
        create_geo_database()


class Test_Geo_Init_Airspace_Operations(unittest.TestCase):
    """
    Test cases against the geo init elemntary sectors
    """
    def test_load_elementary_sectors(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        make_airspace_file = make_test_data_file(AIRSPACE_DATA_FILE)
        ok = load_airspace(make_airspace_file(), context, connection)
        connection_owner = ctx.get_connection(ctx.CONTEXT, ctx.POSTGRES_DB)
        create_GIST_index(context, connection_owner)
        self.assertTrue(ok)
        #
        # Check we actually added some sectors
        #
        schemaName = context[ctx.SCHEMA_NAME]
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(id) FROM %s.sectors;",
                           [AsIs(schemaName)])
            self.assertTrue(cursor.fetchone()[0] > 0)
        connection.close()


class Test_Geo_Init_User_Airspace_Operations(unittest.TestCase):
    """
    Test cases against the geo init user airspace ops
    """

    def test_load_user_airspace(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        make_user_airspace_file = make_test_data_file(USER_DEFINED_AIRSPACES)
        ok = load_user_airspace(make_user_airspace_file(), context, connection)
        connection_owner = ctx.get_connection(ctx.CONTEXT, ctx.POSTGRES_DB)
        create_GIST_index(context, connection_owner)
        self.assertTrue(ok)
        #
        # Check we actually added some user sectors
        #
        schemaName = context[ctx.SCHEMA_NAME]
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(id) FROM %s.user_defined_sectors;",
                           [AsIs(schemaName)])
            self.assertTrue(cursor.fetchone()[0] > 0)
        connection.close()


class Test_Geo_Init_Airports(unittest.TestCase):
    """
    Test cases against airports
    """
    def test_load_airports(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        make_airports_file = make_test_data_file(AIRPORTS_DATA_FILE)
        ok = load_airports(make_airports_file(), context, connection)
        connection_owner = ctx.get_connection(ctx.CONTEXT, ctx.POSTGRES_DB)
        create_GIST_index(context, connection_owner)
        self.assertTrue(ok)
        #
        # Check we actually added some user sectors
        #
        schemaName = context[ctx.SCHEMA_NAME]
        with connection.cursor(cursor_factory=DictCursor) as dict_cursor:
            dict_cursor.execute("SELECT count(id) FROM %s.airports;",
                                [AsIs(schemaName)])
            self.assertTrue(dict_cursor.fetchone()[0] > 0)
            dict_cursor.execute("SELECT *  FROM %s.airports where icao_ap_code = 'EGLL';",
                                [AsIs(schemaName)])
            heathrow = dict_cursor.fetchone()
            latitude = heathrow['latitude']
            longitude = heathrow['longitude']
            icao_code = heathrow['icao_ap_code']
            self.assertEquals(icao_code, 'EGLL')
            self.assertTrue(51.3 < latitude < 51.5)
            self.assertTrue(-0.48 < longitude < -0.44)
        connection.close()


class Test_Geo_Init_Movement_Style_Airports(unittest.TestCase):
    """
    Test cases against the movement style airports
    """
    def test_load_airports(self):
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        make_movements_airports_file = make_test_data_file(MOVEMENTS_REPORTING_AIRPORTS_DATA_FILE)
        ok = load_airports(make_movements_airports_file(), context, connection)
        connection_owner = ctx.get_connection(ctx.CONTEXT, ctx.POSTGRES_DB)
        create_GIST_index(context, connection_owner)
        self.assertTrue(ok)
        #
        # Check we actually added some user sectors
        #
        schemaName = context[ctx.SCHEMA_NAME]
        with connection.cursor(cursor_factory=DictCursor) as dict_cursor:
            dict_cursor.execute("SELECT count(id) FROM %s.airports;",
                                [AsIs(schemaName)])
            self.assertTrue(dict_cursor.fetchone()[0] > 0)
            dict_cursor.execute("SELECT *  FROM %s.airports where icao_ap_code = 'EGLL';",
                                [AsIs(schemaName)])
            heathrow = dict_cursor.fetchone()
            latitude = heathrow['latitude']
            longitude = heathrow['longitude']
            icao_code = heathrow['icao_ap_code']
            self.assertEquals(icao_code, 'EGLL')
            self.assertTrue(51.3 < latitude < 51.5)
            self.assertTrue(-0.48 < longitude < -0.44)
        connection.close()


def suite():
    suite = unittest.TestSuite()

    # This test leaves the database populated with elementary sectors
    suite.addTest(Test_Geo_Operations('test_remove_db_then_create_and_initialise_sectors'))

    #
    # Happy path tests first
    #

    #
    # Elementary sectors
    #
    suite.addTest(Test_Geo_Init_Airspace_Operations('test_load_elementary_sectors'))

    #
    # User defined sectors
    #
    suite.addTest(Test_Geo_Init_User_Airspace_Operations('test_load_user_airspace'))

    #
    # Airports
    #
    suite.addTest(Test_Geo_Init_Airports('test_load_airports'))
    suite.addTest(Test_Geo_Init_Movement_Style_Airports('test_load_airports'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
