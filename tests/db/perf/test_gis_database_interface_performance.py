#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#


#
# Runs a test case intended to find bottle necks in the db code
#
# A database must be available and configured in geo.context.py
#
# TEST_DATA_HOME must point to the local test data directory
#
# To run :
# tests/db/perf/test_gis_database_interface_performance.py
#
import unittest
from pru.gis_database_interface import find_horizontal_sector_intersections
from pru.db.geo.geo_admin import remove_geo_db, create_geo_database, initialise_airspace
# from pru.db.geo.geo_operations import find_airspace_by_database_ID
import geojson
from line_profiler import LineProfiler
from pru.db.geo.geo_operations import find_intersections, find_line_poly_intersection_without_boundary, find_line_poly_intersection_with_boundary

# THIS NEEDS TO BE SET ON THE ENVIRONMENT where you run the tests
# and must point to a directory where the test data files below can be found.
# ie export TEST_DATA_HOME=/path to test data files
TEST_DATA_HOME_ENV = 'TEST_DATA_HOME'

# testing inside atom
TEST_DATA_HOME = '/Users/petemarshall/dev/projects/pru-python/tests/data'

AIRSPACE_DATA_FILE = "ES_428.geojson"
AIRPORTS_DATA_FILE = "airports.csv"
MOVEMENTS_REPORTING_AIRPORTS_DATA_FILE = "movements_reporting_airports.csv"
FLEET_DATA_FILE = "fleet_data_2017-07-01.csv"
USER_DEFINED_AIRSPACES = "user_defined_airspaces.csv"
MAS_05_DATA_FILE = "mas_05_cpr_trajectories_2017-02-05.json"


def make_test_data_file(file_name):
    def get_test_data_home():
        return TEST_DATA_HOME + "/" + file_name
    return get_test_data_home


def prep_test_data(file_name):
    path = make_test_data_file(file_name)()
    with open(path) as gjs:
        # records is a list of maps
        records = geojson.load(gjs)
        return [{'flight_id': record['flight_id'],
                 'lats': record['horizontal_path']['lats'],
                 'lons': record['horizontal_path']['lons'],
                 'min_alt': min(record['altitude_profile']['altitudes']),
                 'max_alt': max(record['altitude_profile']['altitudes'])}
                for record in records['data']]


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


def do_profile(follow=[]):
        def inner(func):
            def profiled_func(*args, **kwargs):
                try:
                    profiler = LineProfiler()
                    profiler.add_function(func)
                    for f in follow:
                        profiler.add_function(f)
                    profiler.enable_by_count()
                    return func(*args, **kwargs)
                finally:
                    profiler.print_stats()
            return profiled_func
        return inner


class TestGISDBIntersectionsStandardPerf(unittest.TestCase):
    """

    """
    @do_profile(follow=[find_horizontal_sector_intersections, find_line_poly_intersection_with_boundary, find_line_poly_intersection_without_boundary, find_intersections])
    def test_find_standard_sector_intersections_perf(self):
        test_data = prep_test_data(MAS_05_DATA_FILE)
        for i in range(10):
            for path in test_data:
                find_horizontal_sector_intersections(path['flight_id'], path['lats'], path['lons'], path['min_alt'], path['max_alt'])


def suite():
    suite = unittest.TestSuite()

    # Start with no sectors
    suite.addTest(TestGeoOperations('test_remove_db_then_create_and_initialise_sectors'))

    # Now add in the full sector list
    suite.addTest(TestGeoOperations('test_initialise_sectors'))

    # Tests against the elementary sectors
    suite.addTest(TestGISDBIntersectionsStandardPerf('test_find_standard_sector_intersections_perf'))

    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
