#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

#
# A suite that brings together all db related tests
# Make sure your python path is set to point at this project
# A database must be present
#
# For unit testing the following must set on the shell, adjust to suite db
# configuration.
#
# Local test settings for geo db
# AIRSPACE_DB_SERVICE_HOST=192.168.0.12
# AIRSPACE_DB_SERVICE_PORT=31904
#
# Local test settings for ref db
# REFERENCE_DB_SERVICE_HOST=192.168.0.12
# REFERENCE_DB_SERVICE_PORT=30807
# Run like : python -m unittest tests.test_db.suite
#

import unittest
import tests.db.test_common_operations as test_common_operations
import tests.db.geo.test_geo_init as test_geo_init
import tests.db.geo.test_geo_operations as test_geo_operations
import tests.db.geo.test_ap_geo_operations as test_ap_geo_operations
import tests.db.ref.test_ref_operations as test_ref_operations
import tests.pru.test_gis_database_interface as test_gis_database_operations


def suite():
    collectedSuite = unittest.TestSuite()

    suites = []
    suites.append(test_common_operations.suite())
    suites.append(test_geo_init.suite())
    suites.append(test_geo_operations.suite())
    suites.append(test_ap_geo_operations.suite())
    suites.append(test_ref_operations.suite())
    suites.append(test_gis_database_operations.suite())
    collectedSuite.addTests(suites)
    return collectedSuite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
