#!/usr/bin/env python
#
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
import unittest
from pru.db.reference.reference_admin import remove_ref_db, create_ref_db, initialise_fleet_data
from pru.db.reference.ref_operations import find_by_keys, insert_aircraft
from pru.db.reference.ref_operations import remove_aircraft, add_fleet_data_file
from pru.db.reference.ref_operations import find_aircraft, find_by_reg_type, find_by_keys
from pru.db.reference.ref_operations import REG_KEY, TYPE_KEY, ADDRESS_KEY
from pru.db.reference.ref_init import add_fleet_record
import pru.db.context as ctx
from datetime import datetime

record1 = ['GZZGG', 'MY-PLANE', '0x999999', '2017-08-01T22:01:59Z']
record2 = ['GZZGG', 'MY-PLANE', '0x888888', '2017-08-01T22:01:59Z']
record3 = ['GZZGG', 'MY-PLANE', '0x777777', '2017-08-01T22:01:59Z']
record4 = ['GZZPP', 'MY-PLANE-2', '0x777776', '2017-08-01T22:01:59Z']


class TestRefOperations(unittest.TestCase):
    """
    Test cases against the ref support operations of the refernce data model.
    """

    def test_remove_db_then_create_and_initialise_fleet(self):
        """
        Completely remove the ref db and recreate
        """
        remove_ref_db()
        create_ref_db()
        initialise_fleet_data("/Users/petemarshall/Downloads/fleet_data_2017-07-01.csv", False)

    def test_add_fleet_data_file(self):
        remove_ref_db()
        create_ref_db()
        add_fleet_data_file("/Users/petemarshall/Downloads/fleet_data_2017-07-01.csv")

    def test_add_record(self):
        """

        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
        context = ctx.CONTEXT
        insert_aircraft(record1[0], record1[1], record1[2], record1[3])
        found, rows = find_by_keys({'AIRCRAFT_REG': 'GZZGG', 'AIRCRAFT_TYPE': 'MY-PLANE', 'AIRCRAFT_ADDRESS': '0x999999'}, context, connection)
        self.assertTrue(found)
        self.assertTrue(len(rows) == 1)
        id = rows[0]['id']
        print(rows[0])
        remove_aircraft(id, context, connection)
        found, rows = find_aircraft(id, context, connection)
        self.assertFalse(found)

    def test_add_same_record(self):
        """
        If the record already exists but has a different address we
        create a new one with a new date.
        If then a record is inserted with the old address we should add it in as a
        new record with a new time stamp.
        """
        connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
        context = ctx.CONTEXT
        insert_aircraft(record1[0], record1[1], record1[2], record1[3])
        found, rows = find_by_keys({'AIRCRAFT_REG': 'GZZGG', 'AIRCRAFT_TYPE': 'MY-PLANE', 'AIRCRAFT_ADDRESS': '0x999999'}, context, connection)
        self.assertTrue(found)
        self.assertTrue(len(rows) == 1)
        self.assertTrue(insert_aircraft(record1[0], record1[1], record1[2], record1[3]))
        print(insert_aircraft(record2[0], record2[1], record2[2], record2[3]))
        now = datetime.today().isoformat(timespec='seconds')
        print(insert_aircraft(record1[0], record1[1], '0x555555', record1[3]))
        print(insert_aircraft(record1[0], record1[1], '0x555555', now + 'Z'))


class TestRefFindOperations(unittest.TestCase):
    def test_find_by_dict(self):
        """ Find using the dict of key values."""
        connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
        context = ctx.CONTEXT
        insert_aircraft(record4[0], record4[1], record4[2], record4[3])
        finder_dict = {REG_KEY: 'GZZPP',
                       TYPE_KEY: 'MY-PLANE-2',
                       ADDRESS_KEY: '0x777776'}
        ok, records = find_by_keys(finder_dict, context, connection)
        self.assertTrue(ok)
        self.assertEquals(1, len(records))
        record = records[0]
        self.assertEquals(5, len(record))
        self.assertEquals(record[2], 'MY-PLANE-2')

    def test_find_by_bad_dict(self):
        """ Find using the dict with bad key"""
        connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
        context = ctx.CONTEXT
        finder_dict = {'REG_KEYZ': 'GZZPP',
                       TYPE_KEY: 'MY-PLANE-2',
                       ADDRESS_KEY: '0x777776'}
        ok, records = find_by_keys(finder_dict, context, connection)
        self.assertFalse(ok)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestRefOperations('test_remove_db_then_create_and_initialise_fleet'))
    suite.addTest(TestRefOperations('test_add_fleet_data_file'))
    suite.addTest(TestRefOperations('test_add_record'))
    suite.addTest(TestRefOperations('test_add_same_record'))

    suite.addTest(TestRefFindOperations('test_find_by_dict'))
    suite.addTest(TestRefFindOperations('test_find_by_bad_dict'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
