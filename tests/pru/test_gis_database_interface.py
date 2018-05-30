#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

import unittest
from pru.gis_database_interface import find_2D_user_airspace_intersections
from pru.gis_database_interface import find_2D_airspace_intersections
from pru.gis_database_interface import find_airport_cylinder_intersection
from pru.gis_database_interface import get_elementary_airspace_name, get_elementary_airspace_altitude_range
from pru.gis_database_interface import get_user_sector_name, get_user_sector_altitude_range
from pru.gis_database_interface import NotFoundException
from pru.db.geo.geo_init import add_user_sector, add_airspace_geometry
from pru.db.geo.geo_init import load_airports, remove_all_airports, load_user_airspace
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database, initialise_airspace
from pru.db.reference.reference_admin import remove_ref_db, create_ref_db, initialise_fleet_data
from pru.db.geo.ap_geo_operations import finder
from pru.db.geo.user_geo_operations import find_by_org_user_name
import pru.db.context as ctx
from os import environ as env

# THIS NEEDS TO BE SET ON THE ENVIRONMENT where you run the tests
# and must point to a directory where the test data files below can be found.
# ie export TEST_DATA_HOME=/path to test data files
TEST_DATA_HOME_ENV = 'TEST_DATA_HOME'

AIRSPACE_DATA_FILE = "ES_428.geojson"
AIRPORTS_DATA_FILE = "airports.csv"
FLEET_DATA_FILE = "fleet_data_2017-07-01.csv"
USER_DEFINED_AIRSPACES = "user_defined_airspaces.csv"


def make_test_data_file(file_name):
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
        make_airspace_file = make_test_data_file(AIRSPACE_DATA_FILE)
        initialise_airspace(make_airspace_file(), False)


class TestGISDBIntersectionsUser(unittest.TestCase):
    """
    Test cases against the intersections operations of the airspace model
    for user defined sectors
    """

    def test_find_user_sector_intersections_non_cylinder(self):

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Define a trajectory
        FLIGHT_ID_1 = "test-id-1"
        MIN_ALT_1 = 1009
        MAX_ALT_1 = 2009
        LATS_1 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_1 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

        FLIGHT_ID_2 = "test-id-2"
        MIN_ALT_2 = 300
        MAX_ALT_2 = 500
        LATS_2 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_2 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

        # Define a custom sector
        ORG_ID = "PRU"
        USER_ID = "user-name-1"
        SECTOR_ID = "test-sector-1-poly"
        MIN_FL = 10
        MAX_FL = 150
        LAT = None
        LON = None
        RADIUS = 0
        IS_CYLINDER = False
        USER_SECTOR_1_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"
        user_sector_1 = [ORG_ID, USER_ID, SECTOR_ID, LAT, LON, RADIUS, MIN_FL, MAX_FL, IS_CYLINDER, USER_SECTOR_1_WKT]

        # Add a custom sector to the user sectors
        ok, sector_1_id = add_user_sector(user_sector_1, context, connection)
        self.assertTrue(ok)

        # Find known intersecting trajectory intersections
        res1 = find_2D_user_airspace_intersections(FLIGHT_ID_1, LATS_1, LONS_1, MIN_ALT_1, MAX_ALT_1)
        self.assertTrue(res1)

        # There should be at least one intersection with our artifical sector
        self.assertTrue(str(sector_1_id) in res1[2])

        # recover the sector ids
        recovered_sector_id_1 = [id for id in res1[2] if str(sector_1_id) == id][0]
        recovered_sector_id_2 = [id for id in res1[2] if str(sector_1_id) == id][1]

        # Find the sector descriptive name
        self.assertEquals("PRU/user-name-1/test-sector-1-poly", get_user_sector_name(recovered_sector_id_1))
        self.assertEquals("PRU/user-name-1/test-sector-1-poly", get_user_sector_name(recovered_sector_id_2))

        # Find the sector altitude ranges
        self.assertEquals((1000, 15000), get_user_sector_altitude_range(recovered_sector_id_1))
        self.assertEquals((1000, 15000), get_user_sector_altitude_range(recovered_sector_id_2))

        # Find known non-intersecting trajectory intersections
        res2 = find_2D_user_airspace_intersections(FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)
        # There should be no intersections with our artificial sector
        self.assertFalse(str(sector_1_id) in res2[2])

    def test_not_found_user_sector_alt_range(self):
        """
        Check the raised exception when the db entry cannot be found
        """
        with self.assertRaises(NotFoundException) as context:
            get_user_sector_altitude_range('99999')
        expected_exception = context.exception
        self.assertEquals("User sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)

    def test_not_found_user_sector_description(self):
        """
        Check the raised exception when the db entry cannot be found
        """
        with self.assertRaises(NotFoundException) as context:
            get_user_sector_name('99999')
        expected_exception = context.exception
        self.assertEquals("User sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)

    def test_load_user_sectors_from_file(self):
        """
        Test we can load a set of user predefined sectors.
        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        make_user_test_sectors_file = make_test_data_file(USER_DEFINED_AIRSPACES)
        load_user_airspace(make_user_test_sectors_file(), context, connection)
        # These vars are in the csv file.
        ORG_ID = 'pru'
        USER_ID1 = 'user1'
        SECTOR_NAME_1 = 'test_sector-111'
        ok, sectors = find_by_org_user_name(ORG_ID, USER_ID1, SECTOR_NAME_1)
        self.assertTrue(ok)
        self.assertEquals(1, len(sectors))
        sector = sectors[0]
        self.assertEquals(sector['radius'], 55560.0)


class TestGISDBIntersectionsStandard(unittest.TestCase):
    """
    Test cases against the intersections operations of the airspace model.
    We can still use our own custom sector shapes.
    """

    def test_find_standard_sector_intersections(self):

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Define a trajectory
        FLIGHT_ID_1 = "test-id-1"
        MIN_ALT_1 = 10090
        MAX_ALT_1 = 20090
        LATS_1 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_1 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

        # This one is above our test sector
        FLIGHT_ID_2 = "test-id-2"
        MIN_ALT_2 = 30000
        MAX_ALT_2 = 60000
        LATS_2 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_2 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

        # Define a sector like the csv sectors in elementary_sectors.csv
        AC_ID = "991"
        AV_AIRSPACE_ID = "ZZPMPMZZAA"
        AV_ICAO_STATE_ID = "LZ"
        MIN_FLIGHT_LEVEL = "100"
        MAX_FLIGHT_LEVEL = "200"
        AV_NAME = "Made Up Sector"
        SECTOR_TYPE = "ES"
        OBJECT_ID = 2209999
        USER_SECTOR_1_WKT = "POLYGON ((-0.3 50.5, 0.3 50.5, 0.3 49.5, -0.3 49.5, -0.3 50.5))"

        # A single row from the csv file
        sector_1 = [AC_ID, AV_AIRSPACE_ID, AV_ICAO_STATE_ID, MIN_FLIGHT_LEVEL, MAX_FLIGHT_LEVEL, AV_NAME, SECTOR_TYPE, OBJECT_ID, USER_SECTOR_1_WKT]

        # Add to the sectors database
        ok, sector_1_id = add_airspace_geometry(sector_1, context, connection)
        self.assertTrue(ok)

        # Find known intersecting trajectory intersections
        res1 = find_2D_airspace_intersections(FLIGHT_ID_1, LATS_1, LONS_1, MIN_ALT_1, MAX_ALT_1)
        self.assertTrue(res1)

        # There should be at least one intersection with our artifical sector
        self.assertTrue(str(sector_1_id) in res1[2])

        # There should be 2 intersections with our sector, in and out, count
        # the occurances of our sector id in the result
        self.assertEquals(2, len([id for id in res1[2] if str(sector_1_id) == id]))

        # recover the sector ids
        recovered_sector_id_1 = [id for id in res1[2] if str(sector_1_id) == id][0]
        recovered_sector_id_2 = [id for id in res1[2] if str(sector_1_id) == id][1]

        # Find the sector descriptive name
        self.assertEquals("LZ/Made Up Sector/3710/ZZPMPMZZAA", get_elementary_airspace_name(recovered_sector_id_1))
        self.assertEquals("LZ/Made Up Sector/3710/ZZPMPMZZAA", get_elementary_airspace_name(recovered_sector_id_2))

        # Find the sector altitude ranges
        self.assertEquals((10000, 20000), get_elementary_airspace_altitude_range(recovered_sector_id_1))
        self.assertEquals((10000, 20000), get_elementary_airspace_altitude_range(recovered_sector_id_2))

        # Find known non-intersecting trajectory intersections
        res2 = find_2D_airspace_intersections(FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)
        # There should be no intersections with our artificial sector
        self.assertFalse(str(sector_1_id) in res2[2])

    def test_not_found_elementary_sector_alt_range(self):
        with self.assertRaises(NotFoundException) as context:
            get_elementary_airspace_altitude_range('99999')
        expected_exception = context.exception
        self.assertEquals("Elementary sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)

    def test_not_found_elementary_sector_description(self):
        with self.assertRaises(NotFoundException) as context:
            get_elementary_airspace_name('99999')
        expected_exception = context.exception
        self.assertEquals("Elementary sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)


class TestGISDBFindIntersectionsUsersCylinders(unittest.TestCase):
    """
    Tests against the custom user sectros cylinders operations
    """

    def test_find_user_cylinder_intersections(self):

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Define a trajectory
        FLIGHT_ID_1 = "test-id-1"
        MIN_ALT_1 = 10090
        MAX_ALT_1 = 20090
        LATS_1 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_1 = [-10.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 10.5]

        # This one is above our test sector
        FLIGHT_ID_2 = "test-id-2"
        MIN_ALT_2 = 30000
        MAX_ALT_2 = 60000
        LATS_2 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_2 = [-10.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 10.5]

        # Define a custom sector
        ORG_ID = "PRU"
        USER_ID = "user-name-1"
        SECTOR_ID = "test-cylinder_user_sector-1-poly"
        MIN_FL = 10
        MAX_FL = 150
        LAT = 50.0
        LON = 0.0
        RADIUS = 20
        IS_CYLINDER = "True"
        USER_SECTOR_1_WKT = ""
        user_cylinder_sector_1 = \
            [ORG_ID, USER_ID, SECTOR_ID, LAT, LON, RADIUS, MIN_FL, MAX_FL,
             IS_CYLINDER, USER_SECTOR_1_WKT]

        # Add a custom sector to the user sectors
        ok, sector_1_id = add_user_sector(user_cylinder_sector_1, context, connection)
        self.assertTrue(ok)

        # Find known intersecting trajectory intersections
        res1 = find_2D_user_airspace_intersections(FLIGHT_ID_1, LATS_1, LONS_1, MIN_ALT_1, MAX_ALT_1)
        self.assertTrue(res1)

        # There should be at least one intersection with our artifical sector
        self.assertTrue(str(sector_1_id) in res1[2])

        # Find the sector descriptive name
        self.assertEquals("PRU/user-name-1/test-cylinder_user_sector-1-poly", get_user_sector_name(sector_1_id))

        # Find the sector altitude range
        self.assertEquals((1000, 15000), get_user_sector_altitude_range(sector_1_id))

        # Find known non-intersecting trajectory intersections
        res2 = find_2D_user_airspace_intersections(FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)
        # There should be no intersections with our artificial sector
        self.assertFalse(str(sector_1_id) in res2[2])

    def test_not_found_user_cylinder_sector_alt_range(self):
        with self.assertRaises(NotFoundException) as context:
            get_user_sector_altitude_range('99999')
        expected_exception = context.exception
        self.assertEquals("User sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)

    def test_not_found_user_cylinder_sector_description(self):
        with self.assertRaises(NotFoundException) as context:
            get_user_sector_name('99999')
        expected_exception = context.exception
        self.assertEquals("User sector not found.", expected_exception.message)
        self.assertEquals('99999', expected_exception.db_id)


class TestGISDBAirportIntersections(unittest.TestCase):
    """
    Test against the airports interface
    """

    def test_load_airports(self):
        """
        Remove all the airports then add them
        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        remove_all_airports()
        make_aps_file = make_test_data_file(AIRPORTS_DATA_FILE)
        load_airports(make_aps_file(), context, connection)

    def test_find_airport_intersections(self):
        """
        Check a simple airport intersection
        """

        RADIUS_1 = 30
        AIRPORT_ID_1 = "NONO"
        AIRPORT_ID_2 = "LFPG"

        ok, airports = finder('icao_ap_code', AIRPORT_ID_2)
        self.assertTrue(ok)
        self.assertEquals(1, len(airports))
        airport = airports[0]
        self.assertEquals(airport['icao_ap_code'], 'LFPG')

        FLIGHT_ID_1 = "test-1-id-1"
        LATS_1 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
        LONS_1 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

        FLIGHT_ID_2 = "test-1-id-2"
        LATS_2 = [49.0, 49.0, 49.0, 49.0, 49.0, 49.0, 49.0, 49.0, 49.0, 49.0, 49.0]
        LONS_2 = [1.5, -1.4, 1.0, 1.2, 1.7, 2.0, 2.1, 2.4, 2.5, 2.6, 2.7]

        # An airport we do not intersect with
        lats, lons = find_airport_cylinder_intersection(FLIGHT_ID_1, LATS_1, LONS_1,
                                                        AIRPORT_ID_1, RADIUS_1, False)
        self.assertEquals(0, len(lats))
        self.assertEquals(0, len(lons))

        # An airport we do intersect with
        lats, lons = find_airport_cylinder_intersection(FLIGHT_ID_2, LATS_2, LONS_2,
                                                        AIRPORT_ID_2, RADIUS_1, False)
        self.assertEquals(1, len(lats))
        self.assertEquals(1, len(lons))


class TestGISDBFleetData(unittest.TestCase):
    """
    Test fleet data interface
    """

    def test_load_fleet_data(self):
        # """
        # Completely remove the ref db and recreate
        # """ 
        remove_ref_db()
        create_ref_db()
        make_fleet_file = make_test_data_file(FLEET_DATA_FILE)
        initialise_fleet_data(make_fleet_file(), False)


def suite():
    suite = unittest.TestSuite()

    # This test leaves the database populated with elementary sectors
    suite.addTest(Test_Geo_Operations('test_remove_db_then_create_and_initialise_sectors'))

    #
    # Happy path tests first
    #

    # Tests against the elementary sectors
    suite.addTest(TestGISDBIntersectionsStandard('test_find_standard_sector_intersections'))
    suite.addTest(TestGISDBIntersectionsStandard('test_not_found_elementary_sector_alt_range'))
    suite.addTest(TestGISDBIntersectionsStandard('test_not_found_elementary_sector_description'))

    # Tests against user non-cylinder sectors
    suite.addTest(TestGISDBIntersectionsUser('test_find_user_sector_intersections_non_cylinder'))
    suite.addTest(TestGISDBIntersectionsUser('test_not_found_user_sector_alt_range'))
    suite.addTest(TestGISDBIntersectionsUser('test_not_found_user_sector_description'))
    suite.addTest(TestGISDBIntersectionsUser('test_load_user_sectors_from_file'))

    # Tests against cylinder sectors
    suite.addTest(TestGISDBFindIntersectionsUsersCylinders('test_find_user_cylinder_intersections'))
    suite.addTest(TestGISDBFindIntersectionsUsersCylinders('test_not_found_user_cylinder_sector_alt_range'))
    suite.addTest(TestGISDBFindIntersectionsUsersCylinders('test_not_found_user_cylinder_sector_description'))

    # Tests against the airport intersections
    suite.addTest(TestGISDBAirportIntersections('test_load_airports'))
    suite.addTest(TestGISDBAirportIntersections('test_find_airport_intersections'))

    # NOT IN THE GEO DB INTERFACE NEEDS TO BE MOVED
    # The Fleet Data operations
    suite.addTest(TestGISDBFleetData('test_load_fleet_data'))

    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())