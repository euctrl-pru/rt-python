#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
import unittest
from pru.db.common_init import create, DB_TYPE_GEO, DB_TYPE_REF
from pru.db.geo.geo_admin import remove_geo_db
from pru.db.reference.reference_admin import remove_ref_db


class Test_Common_Operations(unittest.TestCase):
    """
    Test cases against the common operations on the databases.
    """

    def test_remove_db_then_create(self):
        """
        Completely remove the ref and geo dbs and recreate
        """
        remove_geo_db()
        remove_ref_db()
        create(DB_TYPE_GEO)
        create(DB_TYPE_REF)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(Test_Common_Operations('test_remove_db_then_create'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
