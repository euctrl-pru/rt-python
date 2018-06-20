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
from pru.db.geo.geo_init import add_user_sector, add_airspace_geometry, remove_all_sectors
from pru.db.geo.geo_init import load_airports, remove_all_airports, load_user_airspace
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database, initialise_airspace
from pru.db.reference.reference_admin import remove_ref_db, create_ref_db, initialise_fleet_data
from pru.db.geo.ap_geo_operations import finder
from pru.db.geo.user_geo_operations import find_by_org_user_name
from pru.db.geo.geo_operations import find_airspace_by_database_ID
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


class TestGeoOperations(unittest.TestCase):
    """
    Test cases against the geo support operations of the airspace model.
    """

    def test_remove_db_then_create_and_initialise_sectors(self):
        """
        Completely remove the geo db and recreate
        """
        remove_geo_db()
        create_geo_database()

    def test_initialise_sectors(self):
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
        connection.close()

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
        connection.close()


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
        self.assertEquals("LZ/Made Up Sector/" + str(recovered_sector_id_1) +
                          "/ZZPMPMZZAA",
                          get_elementary_airspace_name(recovered_sector_id_1))
        self.assertEquals("LZ/Made Up Sector/" + str(recovered_sector_id_2) +
                          "/ZZPMPMZZAA",
                          get_elementary_airspace_name(recovered_sector_id_2))

        # Find the sector altitude ranges
        self.assertEquals((10000, 20000), get_elementary_airspace_altitude_range(recovered_sector_id_1))
        self.assertEquals((10000, 20000), get_elementary_airspace_altitude_range(recovered_sector_id_2))

        # Find known non-intersecting trajectory intersections
        res2 = find_2D_airspace_intersections(FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)
        # There should be no intersections with our artificial sector
        self.assertFalse(str(sector_1_id) in res2[2])
        connection.close()

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


class TestGISDBIntersectionsStandardWithSegments(unittest.TestCase):
    """
    Test cases against the intersections operations of the airspace model.
    We can still use our own custom sector shapes.
    """

    # Define a trajectory
    FLIGHT_ID_1 = "test-id-1"
    MIN_ALT_1 = 10090
    MAX_ALT_1 = 20090
    LATS_1 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    LONS_1 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    TRANSIT_FLIGHT = (FLIGHT_ID_1, LATS_1, LONS_1, MIN_ALT_1, MAX_ALT_1)

    # This one is above our test sector
    FLIGHT_ID_2 = "transits_sector_too_high"
    MIN_ALT_2 = 30000
    MAX_ALT_2 = 60000
    LATS_2 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    LONS_2 = [-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    TRANSIT_TOO_HIGH_FLIGHT = (FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)

    # Originates in sector
    FLIGHT_ID_3 = "test-id-3-originates-in-sector"
    MIN_ALT_3 = 10090
    MAX_ALT_3 = 20090
    LATS_3 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    LONS_3 = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.5]
    ORIGINATES_FLIGHT = (FLIGHT_ID_3, LATS_3, LONS_3, MIN_ALT_3, MAX_ALT_3)

    # Terminates in sector
    FLIGHT_ID_4 = "test-id-4-terminates-in-sector"
    MIN_ALT_4 = 10090
    MAX_ALT_4 = 10090
    LATS_4 = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    LONS_4 = [-1.5, -1.2, -0.8, -0.5, -0.4, -0.3, -0.2, -0.1, 0.0]
    TERMINATES_FLIGHT = (FLIGHT_ID_4, LATS_4, LONS_4, MIN_ALT_4, MAX_ALT_4)

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

    # Terminates in combe tang
    FLIGHT_ID_5 = "test-id-5-terminates-in-combe"
    MIN_ALT_5 = 10090
    MAX_ALT_5 = 10090
    LATS_5 = [48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5]
    LONS_5 = [-1.0, -0.4, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.5]
    TERMINATES_IN_COMBE_FLIGHT = (FLIGHT_ID_5, LATS_5, LONS_5, MIN_ALT_5, MAX_ALT_5)

    # Transits the combes
    FLIGHT_ID_6 = "test-id-6-transits_combes"
    MIN_ALT_6 = 10090
    MAX_ALT_6 = 10090
    LATS_6 = [48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5]
    LONS_6 = [-1.0, -0.4, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    TRANSITS_COMBE_FLIGHT = (FLIGHT_ID_6, LATS_6, LONS_6, MIN_ALT_6, MAX_ALT_6)

    # Originates in combe tang but we fly out east to west
    FLIGHT_ID_7 = "test-id-7-originates-in-combe"
    MIN_ALT_7 = 10090
    MAX_ALT_7 = 10090
    LATS_7 = list([48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5, 48.5][::-1])
    LONS_7 = list([-1.0, -0.4, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.5][::-1])
    LATS_7
    LONS_7
    ORIGINATES_IN_COMBE_FLIGHT = (FLIGHT_ID_7, LATS_7, LONS_7, MIN_ALT_7, MAX_ALT_7)

    # Sector shaped like a combe with three teeth
    AC_ID_2 = "992"
    AV_AIRSPACE_ID_2 = "COMBE_SHAPE"
    AV_ICAO_STATE_ID_2 = "CS"
    MIN_FLIGHT_LEVEL_2 = "100"
    MAX_FLIGHT_LEVEL_2 = "200"
    AV_NAME_2 = "Sector like a combe with three teeth"
    SECTOR_TYPE_2 = "ES"
    OBJECT_ID_2 = 2299999
    USER_SECTOR_2_WKT = "POLYGON ((-0.4 50.5, 0.6 50.5, 0.6 48.0, " + \
                        "0.4 48.0, 0.4 49.5, 0.2 49.5, 0.2 48.0, " + \
                        "0.0 48.0, 0.0 49.5, -0.2 49.5, -0.2 48.0, " + \
                        "-0.4 48.0, -0.4 50.5))"

    sector_1 = [AC_ID, AV_AIRSPACE_ID, AV_ICAO_STATE_ID, MIN_FLIGHT_LEVEL,
                MAX_FLIGHT_LEVEL, AV_NAME, SECTOR_TYPE, OBJECT_ID,
                USER_SECTOR_1_WKT]
    sector_2 = [AC_ID_2, AV_AIRSPACE_ID_2, AV_ICAO_STATE_ID_2,
                MIN_FLIGHT_LEVEL_2, MAX_FLIGHT_LEVEL_2, AV_NAME_2,
                SECTOR_TYPE_2, OBJECT_ID_2, USER_SECTOR_2_WKT]

    def test_find_standard_sector_intersections(self):

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Start with no sectors
        remove_all_sectors()

        # Add the simple sector
        ok, sector_1_id = add_airspace_geometry(self.sector_1, context, connection)
        self.assertTrue(ok)

        # Flight terminates in the sector
        terminates = find_2D_airspace_intersections(*self.TERMINATES_FLIGHT)
        terminates_lats = terminates[0]
        terminates_lons = terminates[1]
        terminates_ids = terminates[2]
        self.assertEquals(1, len(terminates_lats))
        self.assertEquals(1, len(terminates_lons))
        self.assertEquals(1, len(terminates_ids))
        sectors = find_airspace_by_database_ID(str(terminates_ids[0]), context, connection)
        self.assertEquals(1, len(sectors))
        self.assertEquals(sectors[0][6], 'Made Up Sector')

        # Flight transits the sector
        transits = find_2D_airspace_intersections(*self.TRANSIT_FLIGHT)
        transit_lats = transits[0]
        transit_lons = transits[1]
        transit_ids = transits[2]
        self.assertEquals(2, len(transit_lats))
        self.assertEquals(2, len(transit_lons))
        self.assertEquals(2, len(transit_ids))

        # Flight transits the sector above the sector
        transits = find_2D_airspace_intersections(*self.TRANSIT_TOO_HIGH_FLIGHT)
        transit_lats = transits[0]
        transit_lons = transits[1]
        transit_ids = transits[2]
        self.assertEquals(0, len(transit_lats))
        self.assertEquals(0, len(transit_lons))
        self.assertEquals(0, len(transit_ids))

        # Flight originates in the sector
        originates = find_2D_airspace_intersections(*self.ORIGINATES_FLIGHT)
        originates_lats = originates[0]
        originates_lons = originates[1]
        originates_ids = originates[2]
        self.assertEquals(2, len(originates_lats))
        self.assertEquals(2, len(originates_lons))
        self.assertEquals(2, len(originates_ids))

    def test_find_standard_sector_intersections_with_segments(self):
        """
        A more complex sector shape.  A combe with three legs.
        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Start with no sectors
        remove_all_sectors()

        # Add combe like sector to the sectors database
        ok, sector_2_id = add_airspace_geometry(self.sector_2, context, connection)
        self.assertTrue(ok)

        # Terminates in the sector
        terminates = find_2D_airspace_intersections(*self.TERMINATES_IN_COMBE_FLIGHT)
        terminates_lats = terminates[0]
        terminates_lons = terminates[1]
        terminates_ids = terminates[2]
        self.assertEquals(5, len(terminates_lats))
        self.assertEquals(5, len(terminates_lons))
        self.assertEquals(5, len(terminates_ids))

        # Transits the sector
        transits = find_2D_airspace_intersections(*self.TRANSITS_COMBE_FLIGHT)
        transit_lats = transits[0]
        transit_lons = transits[1]
        transit_ids = transits[2]
        self.assertEquals(6, len(transit_lats))
        self.assertEquals(6, len(transit_lons))
        self.assertEquals(6, len(transit_ids))

        # Originates in the sector, should be an even number as we add in the
        # position if we originate
        originates = find_2D_airspace_intersections(*self.ORIGINATES_IN_COMBE_FLIGHT)
        origin_lats = originates[0]
        origin_lons = originates[1]
        origin_sector_ids = originates[2]
        self.assertEquals(6, len(origin_lats))
        self.assertEquals(6, len(origin_lons))
        self.assertEquals(6, len(origin_sector_ids))

    def test_find_qudrant_intersections(self):
        """
        Test against a four section (quadrants) airspace.
        See Trajectories Production Airspace Intersections Report Test
        Sectors, page 18.
        """
        AC_ID_A1 = "990"
        AV_AIRSPACE_ID_A1 = "SYNTHA1"
        AV_ICAO_STATE_ID_A1 = "CS"
        MIN_FLIGHT_LEVEL_A1 = "0"
        MAX_FLIGHT_LEVEL_A1 = "200"
        AV_NAME_A1 = "Square A1"
        SECTOR_TYPE_A1 = "ES"
        OBJECT_ID_A1 = 2399999
        SECTOR_A1_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "1.00000000 0.00000000 0.00000000, " + \
                        "1.00000000 1.00000000 0.00000000, " + \
                        "0.00000000 1.000000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_A2 = "989"
        AV_AIRSPACE_ID_A2 = "SYNTHA2"
        AV_ICAO_STATE_ID_A2 = "CS"
        MIN_FLIGHT_LEVEL_A2 = "0"
        MAX_FLIGHT_LEVEL_A2 = "200"
        AV_NAME_A2 = "Square A2"
        SECTOR_TYPE_A2 = "ES"
        OBJECT_ID_A2 = 2399999
        SECTOR_A2_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "-1.000000000 0.000000000 0.00000000, " + \
                        "-1.00000000 1.00000000 0.00000000, " + \
                        "0.000000000 1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_A3 = "979"
        AV_AIRSPACE_ID_A3 = "SYNTHA3"
        AV_ICAO_STATE_ID_A3 = "CS"
        MIN_FLIGHT_LEVEL_A3 = "0"
        MAX_FLIGHT_LEVEL_A3 = "200"
        AV_NAME_A3 = "Square A3"
        SECTOR_TYPE_A3 = "ES"
        OBJECT_ID_A3 = 2399999
        SECTOR_A3_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "-1.000000000 0.000000000 0.00000000, " + \
                        "-1.00000000 -1.00000000 0.00000000, " + \
                        "0.000000000 -1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_A4 = "969"
        AV_AIRSPACE_ID_A4 = "SYNTHA4"
        AV_ICAO_STATE_ID_A4 = "CS"
        MIN_FLIGHT_LEVEL_A4 = "0"
        MAX_FLIGHT_LEVEL_A4 = "200"
        AV_NAME_A4 = "Square A3"
        SECTOR_TYPE_A4 = "ES"
        OBJECT_ID_A4 = 2399999
        SECTOR_A4_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "1.000000000 0.000000000 0.00000000, " + \
                        "1.00000000 -1.00000000 0.00000000, " + \
                        "0.000000000 -1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        sector_A1 = [AC_ID_A1, AV_AIRSPACE_ID_A1, AV_ICAO_STATE_ID_A1, MIN_FLIGHT_LEVEL_A1,
                     MAX_FLIGHT_LEVEL_A1, AV_NAME_A1, SECTOR_TYPE_A1, OBJECT_ID_A1,
                     SECTOR_A1_WKT]

        sector_A2 = [AC_ID_A2, AV_AIRSPACE_ID_A2, AV_ICAO_STATE_ID_A2, MIN_FLIGHT_LEVEL_A2,
                     MAX_FLIGHT_LEVEL_A2, AV_NAME_A2, SECTOR_TYPE_A2, OBJECT_ID_A2,
                     SECTOR_A2_WKT]

        sector_A3 = [AC_ID_A3, AV_AIRSPACE_ID_A3, AV_ICAO_STATE_ID_A3, MIN_FLIGHT_LEVEL_A3,
                     MAX_FLIGHT_LEVEL_A3, AV_NAME_A3, SECTOR_TYPE_A3, OBJECT_ID_A3,
                     SECTOR_A3_WKT]

        sector_A4 = [AC_ID_A4, AV_AIRSPACE_ID_A4, AV_ICAO_STATE_ID_A4, MIN_FLIGHT_LEVEL_A4,
                     MAX_FLIGHT_LEVEL_A4, AV_NAME_A4, SECTOR_TYPE_A4, OBJECT_ID_A4,
                     SECTOR_A4_WKT]

        AC_ID_B1 = "990"
        AV_AIRSPACE_ID_B1 = "SYNTHB1"
        AV_ICAO_STATE_ID_1 = "CS"
        MIN_FLIGHT_LEVEL_1 = "0"
        MAX_FLIGHT_LEVEL_1 = "200"
        AV_NAME_1 = "Square B1"
        SECTOR_TYPE_1 = "ES"
        OBJECT_ID_1 = 2399999
        SECTOR_B1_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "1.00000000 0.00000000 0.00000000, " + \
                        "1.00000000 1.00000000 0.00000000, " + \
                        "0.00000000 1.000000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_B2 = "989"
        AV_AIRSPACE_ID_B2 = "SYNTHB2"
        AV_ICAO_STATE_ID_2 = "CS"
        MIN_FLIGHT_LEVEL_2 = "0"
        MAX_FLIGHT_LEVEL_2 = "200"
        AV_NAME_2 = "Square B2"
        SECTOR_TYPE_2 = "ES"
        OBJECT_ID_2 = 2399999
        SECTOR_B2_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "-1.000000000 0.000000000 0.00000000, " + \
                        "-1.00000000 1.00000000 0.00000000, " + \
                        "0.000000000 1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_B3 = "979"
        AV_AIRSPACE_ID_B3 = "SYNTHB3"
        AV_ICAO_STATE_ID_3 = "CS"
        MIN_FLIGHT_LEVEL_3 = "0"
        MAX_FLIGHT_LEVEL_3 = "200"
        AV_NAME_3 = "Square B3"
        SECTOR_TYPE_3 = "ES"
        OBJECT_ID_3 = 2399999
        SECTOR_B3_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "-1.000000000 0.000000000 0.00000000, " + \
                        "-1.00000000 -1.00000000 0.00000000, " + \
                        "0.000000000 -1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        AC_ID_B4 = "969"
        AV_AIRSPACE_ID_B4 = "SYNTHB4"
        AV_ICAO_STATE_ID_4 = "CS"
        MIN_FLIGHT_LEVEL_4 = "0"
        MAX_FLIGHT_LEVEL_4 = "200"
        AV_NAME_4 = "Square B4"
        SECTOR_TYPE_4 = "ES"
        OBJECT_ID_4 = 2399999
        SECTOR_B4_WKT = "POLYGON Z (( 0.00000000 0.00000000 0.00000000, " + \
                        "1.000000000 0.000000000 0.00000000, " + \
                        "1.00000000 -1.00000000 0.00000000, " + \
                        "0.000000000 -1.00000000 0.00000000, " + \
                        "0.00000000 0.00000000 0.00000000))"

        sector_B1 = [AC_ID_B1, AV_AIRSPACE_ID_B1, AV_ICAO_STATE_ID_1, MIN_FLIGHT_LEVEL_1,
                     MAX_FLIGHT_LEVEL_1, AV_NAME_1, SECTOR_TYPE_1, OBJECT_ID_1,
                     SECTOR_B1_WKT]

        sector_B2 = [AC_ID_B2, AV_AIRSPACE_ID_B2, AV_ICAO_STATE_ID_2, MIN_FLIGHT_LEVEL_2,
                     MAX_FLIGHT_LEVEL_2, AV_NAME_2, SECTOR_TYPE_2, OBJECT_ID_2,
                     SECTOR_B2_WKT]
        sector_B3 = [AC_ID_B3, AV_AIRSPACE_ID_B3, AV_ICAO_STATE_ID_3, MIN_FLIGHT_LEVEL_3,
                     MAX_FLIGHT_LEVEL_3, AV_NAME_3, SECTOR_TYPE_3, OBJECT_ID_3,
                     SECTOR_B3_WKT]

        sector_B4 = [AC_ID_B4, AV_AIRSPACE_ID_B4, AV_ICAO_STATE_ID_4, MIN_FLIGHT_LEVEL_4,
                     MAX_FLIGHT_LEVEL_4, AV_NAME_4, SECTOR_TYPE_4, OBJECT_ID_4,
                     SECTOR_B4_WKT]

        # test trajectory, southwest to north east
        FLIGHT_ID_1 = "sw-ne"
        MIN_ALT_1 = 0
        MAX_ALT_1 = 600
        LATS_1 = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        LONS_1 = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        FLIGHT_SW_NE = (FLIGHT_ID_1, LATS_1, LONS_1, MIN_ALT_1, MAX_ALT_1)

        # test trajectory, south to north
        FLIGHT_ID_2 = "s-n"
        MIN_ALT_2 = 0
        MAX_ALT_2 = 600
        LATS_2 = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
        LONS_2 = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        FLIGHT_S_N = (FLIGHT_ID_2, LATS_2, LONS_2, MIN_ALT_2, MAX_ALT_2)

        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT

        # Start with no sectors
        remove_all_sectors()

        ok1, sector_1_id = add_airspace_geometry(sector_B1, context, connection)
        self.assertTrue(ok1)
        ok2, sector_2_id = add_airspace_geometry(sector_B2, context, connection)
        self.assertTrue(ok2)
        ok3, sector_3_id = add_airspace_geometry(sector_B3, context, connection)
        self.assertTrue(ok3)
        ok4, sector_4_id = add_airspace_geometry(sector_B4, context, connection)
        self.assertTrue(ok4)

        quad_sectors = [sector_1_id, sector_2_id, sector_3_id, sector_4_id]

        sector_b_sw_ne_intersections = find_2D_airspace_intersections(*FLIGHT_SW_NE)
        # We should find six points of intersection, 1 at the sw corner, 4 in
        # the middle and 1 at the ne corner.
        self.assertEquals(6, len(sector_b_sw_ne_intersections[0]))

        sector_b_s_n_intersections = find_2D_airspace_intersections(*FLIGHT_S_N)
        # Should find 4 intersections, 1 at southern boundary,
        # 2 in the common boundary and 1 at the northern boundary.
        self.assertEquals(4, len(sector_b_s_n_intersections[0]))

        # This last test indicates a problem in ordering.


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
        connection.close()

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

    def test_load_movement_reporting_airports(self):
        """
        Remove all the airports then add them
        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
        context = ctx.CONTEXT
        remove_all_airports()
        make_aps_file = make_test_data_file(MOVEMENTS_REPORTING_AIRPORTS_DATA_FILE)
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

    # Start with no sectors
    suite.addTest(TestGeoOperations('test_remove_db_then_create_and_initialise_sectors'))

    #
    # Happy path tests first
    #

    # Test against a simple sector
    suite.addTest(TestGISDBIntersectionsStandardWithSegments('test_find_standard_sector_intersections'))

    # Test against a combe like sector with transit, originate and terminate trajectoris
    suite.addTest(TestGISDBIntersectionsStandardWithSegments('test_find_standard_sector_intersections_with_segments'))

    # Test with the quadrant sectors described in the Trajectories Production Airspace Intersections Report
    suite.addTest(TestGISDBIntersectionsStandardWithSegments('test_find_qudrant_intersections'))

    # Tests against the elementary sectors
    suite.addTest(TestGISDBIntersectionsStandard('test_find_standard_sector_intersections'))

    # Now add in the full sector list
    suite.addTest(TestGeoOperations('test_initialise_sectors'))

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

    # Tests against the airport intersections using csv input format
    suite.addTest(TestGISDBAirportIntersections('test_load_airports'))
    suite.addTest(TestGISDBAirportIntersections('test_find_airport_intersections'))

    # Tests against the movement reporting airports input format
    suite.addTest(TestGISDBAirportIntersections('test_load_movement_reporting_airports'))

    # TODO NOT IN THE GEO DB INTERFACE NEEDS TO BE MOVED
    # The Fleet Data operations
    suite.addTest(TestGISDBFleetData('test_load_fleet_data'))

    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
