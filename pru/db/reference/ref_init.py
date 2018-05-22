#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Database inititialisation code for the reference db.  This creates the
tables and allows fleet data to be added.
"""

from pru.db.io import read_fleet_records
import pru.db.context as ctx
from pru.logger import logger
from psycopg2.extensions import AsIs
from psycopg2 import OperationalError, Error, ProgrammingError, DataError, InternalError, IntegrityError


log = logger(__name__)


def remove_all_reference_data():
    """
    Deletes all the sectors in the sectors table.
    """
    try:
        db_user_connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
    except OperationalError:
        log.error("Could not get connection, probaly the user does not exist")
        return False
    try:
        schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
        with db_user_connection.cursor() as cursor:
            cursor.execute("DELETE FROM %s.fleet;", [schema_name])
    except ProgrammingError:
        log.exception('Failed to remove fleet data, table does not exist.')
        return False
    finally:
        db_user_connection.close()
    return True


def tear_down():
    """
    Completely tears down the working database.  There must be no open
    connections to the database.
    """
    log.info("Tearing down the reference database")
    postgres_connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_POSTGRES)
    database_name = AsIs(ctx.CONTEXT[ctx.DB_NAME])
    schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
    admin_name = AsIs(ctx.CONTEXT[ctx.ADMIN_NAME])
    user_name = AsIs(ctx.CONTEXT[ctx.USER_NAME])
    with postgres_connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS %s.fleet;", [schema_name])
        cursor.execute("DROP SCHEMA IF EXISTS %s;", [schema_name])
        cursor.execute("SELECT pg_terminate_backend "
                       "(pg_stat_activity.pid) FROM "
                       "pg_stat_activity WHERE datname = current_database() "
                       "AND pid <> pg_backend_pid();")
    try:
        with postgres_connection.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS %s;", [database_name])
            cursor.execute("DROP ROLE IF EXISTS %s;", [user_name])
            cursor.execute("DROP ROLE IF EXISTS %s;", [admin_name])
    except OperationalError:
        log.exception('Failed to drop database or roles.')
        return False
    finally:
        postgres_connection.close()
    log.info("Completed tearing down the reference database")
    return True


def create_fleet_table(context, connection):
    """
    Creates a table of fleet data
    """
    log.info("Creating the fleet table.")

    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    admin_name = AsIs(context[ctx.ADMIN_NAME])
    user_name = AsIs(context[ctx.USER_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE %s.fleet"
                           "(id SERIAL PRIMARY KEY,"
                           "AIRCRAFT_REG varchar(20) NOT NULL,"
                           "AIRCRAFT_TYPE varchar(20) NOT NULL,"
                           "AIRCRAFT_ADDRESS varchar(20),"
                           "PERIOD_START timestamp without time zone);", [schema_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, user_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.fleet TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.fleet TO %s;",
                           [schema_name, user_name])
        return True
    except Error:
        log.exception("Failed trying to make the fleet table")
        return False


def add_fleet_record(fleet_record, context, connection):
    """
    Adds a fleet data rectord to the fleet database.
    Returns True, db_id
    or False, _
    """
    schemaName = AsIs(context[ctx.SCHEMA_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO %s.fleet (AIRCRAFT_REG, AIRCRAFT_TYPE,"
                           "AIRCRAFT_ADDRESS, "
                           "PERIOD_START) VALUES "
                           "(%s, %s, %s, %s) RETURNING id;",
                           (schemaName, str(fleet_record[0]), fleet_record[1],
                            fleet_record[2],
                            fleet_record[3]))
            id = cursor.fetchone()[0]
    except DataError:
        log.exception(f"Failed to add fleet record {fleet_record}"
                      "to fleet table - DataError.")
        return False, f"Failed to add fleet record {fleet_record}" + \
                      "to fleet table - DataError."
    except ValueError:
        log.exception(f"Failed to add fleet record {fleet_record}"
                      "to fleet table - ValueError.")
        return False, f"Failed to add fleet record {fleet_record}" + \
                      "to fleet table - ValueError."
    except InternalError:
        log.exception(f"Failed to add fleet record {fleet_record}"
                      "to fleet table - InternalError.")
        return False, f"Failed to add fleet record {fleet_record}" + \
                      "to fleet table - InternalError."
    except IntegrityError:
        log.exception(f"Failed to add fleet record {fleet_record}"
                      "to fleet table - IntegrityError")
        return False, f"Failed to add fleet record {fleet_record}" + \
                      "to fleet table - IntegrityError"
    return True, id


def load_fleet_data(fleet_file, context, connection):
    """
    Load the fleet file if found else return False.
    """
    if fleet_file:
        log.info(f"Loading the fleet data base using file : {fleet_file}")
        try:
            fleet_records = read_fleet_records(fleet_file)
            # Drop the first line, its always a header line
            next(fleet_records)
            count = 0
            bad_records = []
            for fleet_record in fleet_records:
                if add_fleet_record(fleet_record, context, connection):
                    count += 1
                else:
                    bad_records.append(fleet_record)
            bad_record_count = len(bad_records)
            log.info(f"Made {count} fleet data entries")
            log.info(f"Failed to make {bad_record_count} fleet data entries")
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


def create():
    """
    Creates the complete reference database from scratch.
    """
    context = ctx.CONTEXT
    postgres_admin_connection = ctx.get_connection(context, ctx.REF_POSTGRES_DB)
    log.info("Creating the fleet tables")
    ref_ok = create_fleet_table(context, postgres_admin_connection)
    postgres_admin_connection.close()
    return ref_ok
