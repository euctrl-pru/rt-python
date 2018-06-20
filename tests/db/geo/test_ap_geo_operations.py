#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

# THIS NEEDS TO BE SET ON THE ENVIRONMENT where you run the tests
# and must point to a directory where the test data files below can be found.
# ie export TEST_DATA_HOME=/path to test data files
import unittest
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database
from pru.db.geo.ap_geo_operations import finder
from pru.db.geo.geo_init import load_airports
from pru.db.geo.geo_init import create_GIST_index
import pru.db.context as ctx
from psycopg2.extras import DictCursor
from psycopg2.extensions import AsIs
from os import environ as env

TEST_DATA_HOME_ENV = 'TEST_DATA_HOME'

MOVEMENTS_REPORTING_AIRPORTS_DATA_FILE = "movements_reporting_airports.csv"


def make_test_data_file(file_name):
    def get_test_data_home():
        return env.get(TEST_DATA_HOME_ENV) + "/" + file_name
    return get_test_data_home


class Test_Geo_Operations(unittest.TestCase):
    """
    Test cases against the geo support operations of the airspace model.
    """

    def test_remove_db_then_create(self):
        """
        Completely remove the geo db and recreate
        """
        remove_geo_db()
        create_geo_database()


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


class Test_AP_Geo_Operations(unittest.TestCase):

    def test_finder(self):
        KEY_AIRPORT_CODE = 'icao_ap_code'
        EGLL = 'EGLL'
        ok, airports = finder(KEY_AIRPORT_CODE, EGLL)
        self.assertTrue(ok)
        heathrow = airports[0]
        icao_ap_code = heathrow['icao_ap_code']
        latitude = heathrow['latitude']
        longitude = heathrow['longitude']
        self.assertEquals(icao_ap_code, 'EGLL')
        self.assertTrue(51.3 < latitude < 51.5)
        self.assertTrue(-0.48 < longitude < -0.44)
        self.assertTrue(heathrow['iso_ct_code'] is None)


def suite():
    suite = unittest.TestSuite()

    # This test removes and recreates the database
    suite.addTest(Test_Geo_Operations('test_remove_db_then_create'))
    # Add the airports
    suite.addTest(Test_Geo_Init_Movement_Style_Airports('test_load_airports'))

    # Finder happy path tests
    suite.addTest(Test_AP_Geo_Operations('test_finder'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
