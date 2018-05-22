#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Basic databse operations for the reference data.
Finders
Uniquness logic
"""
import pru.db.context as ctx
from pru.logger import logger
from pru.db.io import read_fleet_records
from pru.db.reference.ref_init import add_fleet_record
from psycopg2.extensions import AsIs
from psycopg2.extras import DictCursor

REG_KEY = 'AIRCRAFT_REG'
REG_KEY = 'AIRCRAFT_TYPE'
ADDRESS_KEY = 'AIRCRAFT_ADDRESS'

KEYS = {REG_KEY, REG_KEY, ADDRESS_KEY}

log = logger(__name__)


def remove_aircraft(db_id, context, connection):
    """
    Remove a fleet record by db id.
    """
    schema_name = context[ctx.SCHEMA_NAME]
    sql = "DELETE FROM %s.fleet where id=%s;"
    params = [AsIs(schema_name), db_id]
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
        return True
    except Exception:
        log.exception(f"Failed to delete record with id: {db_id}  : Exception")
        return False, f"Failed to delete record with id: {db_id}  : Exception"


def find_aircraft(db_id, context, connection):
    """
    Find a fleet record by db id.
    """
    if db_id:
        schema_name = context[ctx.SCHEMA_NAME]
        sql = "select * from %s.fleet where id=%s;"
        params = [AsIs(schema_name), db_id]
        try:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(sql, params)
                res = cursor.fetchmany()
                if res:
                    return True, res
                else:
                    return False, "Not found"
        except Exception:
            log.exception("Failed to find  : Exception")
            return False, "Failed to find  : Exception"
    else:
        return False, "No db_id provided"


def find_by_keys(name_values, context, connection):
    """
    Find by combination of keys:
    If a key is unknown we return a tuple of False, Error Message
    """
    schema_name = context[ctx.SCHEMA_NAME]
    if name_values:
        select = "select * from %s.fleet where AIRCRAFT_REG=%s and AIRCRAFT_TYPE=%s and AIRCRAFT_ADDRESS=%s;"
        params = [AsIs(schema_name), name_values['AIRCRAFT_REG'], name_values['AIRCRAFT_TYPE'], name_values['AIRCRAFT_ADDRESS']]
        try:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(select, params)
                res = cursor.fetchmany()
                if res:
                    return True, res
                else:
                    return False, "Not found"
        except Exception:
            log.exception("Failed to find  : Exception")
            return False, "Failed to find  : Exception"
    else:
        return False, "No key_value_map provided"


def find_by_reg_type(reg, type, context, connection):
    """
    Find by combination of keys:
    If a key is unknown we return a tuple of False, Error Message
    """
    schema_name = context[ctx.SCHEMA_NAME]
    select = "select * from %s.fleet where AIRCRAFT_REG=%s and AIRCRAFT_TYPE=%s;"
    params = [AsIs(schema_name), reg, type]
    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(select, params)
            res = cursor.fetchmany()
            if res:
                return True, res
            else:
                return False, "Not found"
    except Exception:
        log.exception("Failed to find  : Exception")
        return False, "Failed to find  : Exception"


def insert_aircraft(registration, type, address, date_time):
    """
    Inserts a new record into the fleet data.

    returns True db_id
            False, "Error message"
    """
    log.debug(f"Attempting to insert fleet record {registration}, {type}, {address}, {date_time}")
    connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
    context = ctx.CONTEXT
    str_record = str([registration, type, address, date_time])
    # Note http://initd.org/psycopg/docs/usage.html with statement
    # Does not work as described.  Exiting this with will close the connection
    with connection:
        # Does the combination of registration and type exist already?
        found, res = find_by_reg_type(registration, type, context, connection)
        if found:
            # Is this a new address?
            found_address, results = find_by_keys({'AIRCRAFT_REG': registration,
                                                   'AIRCRAFT_TYPE': type,
                                                   'AIRCRAFT_ADDRESS': address},
                                                  context, connection)
            if not found_address:
                # This is a new address so add it.
                ok, id = add_fleet_record([registration, type, address, date_time], context, connection)
                log.debug(f"A fleet data entry was created for {str_record}, id : {id}")
                return ok, id
            else:
                log.debug(f"Fleet record {str_record} not inserted, already exists.")
                return False, f"Fleet record {str_record} not inserted, already exists with given addresss."
        else:
            # We can just add this record since the reg and type combination is new.
            ok, id = add_fleet_record([registration, type, address, date_time], context, connection)
            log.debug(f"Inserted fleet record {str_record}, it was not present")
            return [(False, "New fleet record but failed to add."), (ok, id)][ok]


def add_fleet_data_file(fleet_file):
    """
    Add the fleet file if found else return False.
    """
    if fleet_file:
        log.info(f"Adding the fleet data base using file : {fleet_file}")
        try:
            fleet_records = read_fleet_records(fleet_file)
            # Drop the title row
            next(fleet_records)
            count = 0
            bad_records = []
            for fleet_record in fleet_records:
                ok, id = insert_aircraft(*fleet_record)
                if ok:
                    count += 1
                else:
                    bad_records.append(fleet_record)
            bad_record_count = len(bad_records)
            log.info(f"Made {count} fleet data insertions")
            log.info(f"Failed to make {bad_record_count} fleet data insertions")
            if bad_record_count > 0:
                log.debug("Bad records list:")
                [log.debug(bad_record) for bad_record in bad_records]
            return True
        except Exception:
            log.exception(f"Failed to read fleet data init file : {fleet_file}"
                          " either the file or the directory does not exist.")
            return False
    else:
        log.info("No fleet file provided")
        return False
