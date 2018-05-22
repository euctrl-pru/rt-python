#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Database inititialisation code for the geo db.

Creates the airspace sectors,
airports and user defined sectors tables.

Provides operations to completely remove the tables.

Operations are provided to add rows to each table when the tables are
initialise from files of data.

"""
from pru.db.io import read_airports_records, read_sectors
from pru.db.common_operations import NM_CONVERSION_TO_M, create_buffer
import pru.db.context as ctx
from pru.logger import logger
from psycopg2.extensions import AsIs
from psycopg2 import DataError, InternalError, OperationalError, Error, ProgrammingError, IntegrityError


log = logger(__name__)


def remove_all_sectors():
    """
    Deletes all the sectors in the sectors table.
    """
    log.info("removing all sectors.")
    try:
        db_user_connection = ctx.get_connection(ctx.CONTEXT,
                                                ctx.DB_USER)
    except OperationalError:
        log.error("Could not get connection, probaly the user does not exist")
        return False
    try:
        schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
        with db_user_connection.cursor() as cursor:
            cursor.execute("DELETE FROM %s.sectors;", [schema_name])
    except ProgrammingError:
        log.exception("Failed to delete the sectors table data, perhaps it does not exist?")
        return False
    finally:
        db_user_connection.close()
    return True


def remove_all_user_defined_sectors():
    """
    Deletes all the sectors in the sectors table.
    """
    log.info("removing all sectors.")
    try:
        db_user_connection = ctx.get_connection(ctx.CONTEXT,
                                                ctx.DB_USER)
        schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
        with db_user_connection.cursor() as cursor:
            cursor.execute("DELETE FROM %s.user_defined_sectors;", [schema_name])
    except ProgrammingError:
        log.exception("Failed to delete the sectors table data, perhaps it does not exist?")
        return False
    finally:
        db_user_connection.close()
    return True


def remove_all_airports():
    """
    Deletes all the airports in the airports table.
    """
    log.info("removing all airports.")
    try:
        db_user_connection = ctx.get_connection(ctx.CONTEXT,
                                                ctx.DB_USER)
    except OperationalError:
        log.error("Could not get connection, probaly the user does not exist")
        return False
    try:
        schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
        with db_user_connection.cursor() as cursor:
            cursor.execute("DELETE FROM %s.airports;", [schema_name])
    except ProgrammingError:
        log.exception("Failed to delete the airports table data, perhaps it does not exist?")
        return False
    finally:
        db_user_connection.close()
    return True


def tear_down():
    """
    Completely tears down the working database, in doing so
    will close all the connections (excpet this one!!)
    Use the postgres connection for this call.
    """
    log.info("Tearing down the geo database")
    postgres_connection = ctx.get_connection(ctx.CONTEXT, ctx.POSTGRES)
    database_name = AsIs(ctx.CONTEXT[ctx.DB_NAME])
    schema_name = AsIs(ctx.CONTEXT[ctx.SCHEMA_NAME])
    admin_name = AsIs(ctx.CONTEXT[ctx.ADMIN_NAME])
    user_name = AsIs(ctx.CONTEXT[ctx.USER_NAME])
    with postgres_connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS %s.sectors;", [schema_name])
        cursor.execute("DROP TABLE IF EXISTS %s.airports;", [schema_name])
        cursor.execute("DROP TABLE IF EXISTS %s.user_defined_sectors;", [schema_name])
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
    log.info("Completed tearing down the geo database")
    return True


def make_db_spatial(context, connection):
    """
    Makes the database into a gis database with access by admin and
    user roles.
    """
    log.info('Adding GIS capabilities to the db.')
    adminRole = context[ctx.ADMIN_NAME]
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION postgis;")
    except Error:
        log.exception("Failed to create extension : postgis")
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION postgis_topology;")
    except Error:
        log.exception("Failed to create extension : postgis_topology")
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION postgis_sfcgal;")
    except Error:
        log.exception('Failed to add the postgis_sfcgal extension, ' +
                      'please check that this db image has the sfcgal' +
                      'capability built in.')
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION fuzzystrmatch;")
            cursor.execute("GRANT ALL ON geometry_columns TO %s;",
                           [AsIs(adminRole)])
            cursor.execute("GRANT SELECT ON spatial_ref_sys TO %s;",
                           [AsIs(adminRole)])
            cursor.execute("GRANT ALL ON geometry_columns TO %s;",
                           [AsIs(adminRole)])
        return True
    except Error:
        log.exception("Failed to make the db spatial.")
        return False


def create_airspace_table(context, connection):
    """
    Creates a table of airspaces as a geographic table.
    """
    log.info('Creating the airspace table.')

    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    admin_name = AsIs(context[ctx.ADMIN_NAME])
    user_name = AsIs(context[ctx.USER_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE %s.sectors "
                           "(id SERIAL PRIMARY KEY,"
                           "ac_id int,"
                           "av_airspace_id varchar (20),"
                           "av_icao_state_id varchar(2),"
                           "min_altitude int,"
                           "max_altitude int,"
                           "av_name varchar(100),"
                           "sector_type varchar(2),"
                           "object_id int,"
                           "wkt geometry);", [schema_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, user_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.sectors TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.sectors TO %s;",
                           [schema_name, user_name])
        return True
    except Error:
        log.exception("Failed trying to make the sectors table geographic")
        return False


def create_user_sector_table(context, connection):
    """
    Creates a table of user defined sectors as a geographic table.
    """
    log.info('Creating the user defined sectors table.')

    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    admin_name = AsIs(context[ctx.ADMIN_NAME])
    user_name = AsIs(context[ctx.USER_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE %s.user_defined_sectors "
                           "(id SERIAL PRIMARY KEY,"
                           "org_id varchar(100) NOT NULL DEFAULT 'pru',"
                           "user_id varchar (100) NOT NULL,"
                           "sector_name varchar (100) NOT NULL,"
                           "latitude float,"
                           "longitude float,"
                           "radius float,"
                           "min_altitude int NOT NULL,"
                           "max_altitude int NOT NULL,"
                           "is_cylinder boolean NOT NULL DEFAULT FALSE,"
                           "wkt geometry, "
                           "UNIQUE(org_id, user_id, sector_name));", [schema_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, user_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.user_defined_sectors TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.user_defined_sectors TO %s;",
                           [schema_name, user_name])
        return True
    except Error:
        log.exception("Failed trying to make the user defined sectors table geographic")
        return False


def add_airspace_geometry(airspace, context, connection):
    """
    Adds an airspace description to the airspace database.
    """
    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO %s.sectors (ac_id, av_airspace_id, "
                           "av_icao_state_id, "
                           "min_altitude, max_altitude, "
                           "av_name, sector_type, object_id, wkt) VALUES "
                           "(%s, %s, %s, %s, %s, %s, %s, %s, "
                           "ST_GEOMFROMTEXT((%s), 4326)) RETURNING id;",
                           (schema_name, str(airspace[0]), airspace[1],
                            airspace[2],
                            100 * int(airspace[3]),
                            100 * int(airspace[4]),
                            airspace[5], airspace[6], airspace[7],
                            airspace[8]))
            id = cursor.fetchone()[0]
    except DataError:
        log.exception('Failed to add airspace record ' + str(airspace) +
                      'to airspace table - DataError.')
        return False
    except ValueError:
        log.exception('Failed to add airspace record ' + str(airspace) +
                      'to airspace table - ValueError.')
        return False
    except InternalError:
        log.exception('Failed to add airspace record ' + str(airspace) +
                      'to airspace table - InternalError.')
        return False
    return True, id


def create_airports_table(context, connection):
    """
    Creates a table of airports as a geographic table.
    """
    log.info('Creating the airports table.')

    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    admin_name = AsIs(context[ctx.ADMIN_NAME])
    user_name = AsIs(context[ctx.USER_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE %s.airports "
                           "(id SERIAL PRIMARY KEY,"
                           "iata_ap_code varchar(20),"
                           "icao_ap_code varchar(20),"
                           "iso_ct_code varchar(2),"
                           "latitude float,"
                           "longitude float);", [schema_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %s TO %s;",
                           [schema_name, user_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.airports TO %s;",
                           [schema_name, admin_name])
            cursor.execute("GRANT ALL PRIVILEGES ON %s.airports TO %s;",
                           [schema_name, user_name])
        return True
    except Error:
        log.exception("Failed trying to make the airports table geographic")
        return False


def add_airport(airport, context, connection):
    """
    Adds an airport description to the airport table.
    """
    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO %s.airports (iata_ap_code, "
                           "icao_ap_code, iso_ct_code, latitude, "
                           "longitude) VALUES "
                           "(%s, %s, %s, %s, %s) RETURNING id;",
                           (schema_name, airport[0], airport[1], airport[2],
                            float(airport[3]), float(airport[4])))
            id = cursor.fetchone()[0]
    except DataError:
        log.exception('Failed to add airport record ' + str(airport) +
                      'to airport table - DataError.')
        return False
    except ValueError:
        log.warning('Failed to add airport record ' + str(airport) +
                    'to airport table - ValueError.')
        return False
    except InternalError:
        log.exception('Failed to add airport record ' + str(airport) +
                      'to airport table - InternalError.')
        return False
    return True, id


def create_user_sector_parameters(schema_name, user_sector, connection):
    """
    Creates a parameter list from the given user sector.
    """
    org_id = user_sector[0]
    user_id = user_sector[1]
    sector_name = user_sector[2]
    lat = user_sector[3]
    try:
        lat = float(lat)
    except (ValueError, TypeError) as e:
        lat = 0.0
    lon = user_sector[4]
    try:
        lon = float(lon)
    except (ValueError, TypeError) as e:
        lon = 0.0
    radius = float(user_sector[5])
    radius = radius * NM_CONVERSION_TO_M
    min_fl = 100 * int(user_sector[6])
    max_fl = 100 * int(user_sector[7])
    is_cylinder_text = user_sector[8]
    is_cylinder = is_cylinder_text in ["True", "true", "t", "T", "TRUE"]
    wkt = user_sector[9]
    # is this a cylinder or a wkt sectors
    if is_cylinder:
        # cylinder - make a wkt point from the lat lon
        buffer = create_buffer(lon, lat, radius, connection)
        return (schema_name, org_id, user_id,
                sector_name, lat,
                lon, radius,
                min_fl,
                max_fl,
                True, buffer)
    else:
        return (schema_name, org_id, user_id,
                sector_name, lat,
                lon, radius,
                min_fl,
                max_fl,
                False, wkt)


def add_user_sector(user_sector, context, connection):
    """
    Adds an user sector description to the user defined sectors table.
    """
    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO %s.user_defined_sectors (org_id, "
                           "user_id, sector_name, latitude, longitude, "
                           "radius, min_altitude, "
                           "max_altitude, is_cylinder, wkt) VALUES "
                           "(%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                           "ST_GEOMFROMTEXT((%s), 4326)) RETURNING id;",
                           create_user_sector_parameters(schema_name, user_sector, connection))
            id = cursor.fetchone()[0]
    except DataError:
        log.exception(f"Failed to add user sector {user_sector}"
                      "to user defined sectors table - DataError.")
        return False, f"Failed to add fuser sector {user_sector}" + \
                      "to user defined sectors table - DataError."
    except ValueError:
        log.exception(f"Failed to add user sector {user_sector}"
                      "to user defined sectors table - ValueError.")
        return False, f"Failed to add user sector {user_sector}" + \
                      "to user defined sectors table - ValueError."
    except InternalError:
        log.exception(f"Failed to add user sector {user_sector}"
                      "to user defined sectors table - InternalError.")
        return False, f"Failed to add user sector {user_sector}" + \
                      "to user defined sectors table - InternalError."
    except IntegrityError:
        log.exception(f"Failed to add user sector {user_sector}"
                      "to user defined sectors table - IntegrityError")
        return False, f"Failed to add user sector {user_sector}" + \
                      "to user defined sectors table - IntegrityError"
    return True, id


def create_GIST_index(context, connection):
    """
    Creates or recreates a GIST index on the geom column of the
    airspace table.
    """
    cursor = connection.cursor()
    schema_name = AsIs(context[ctx.SCHEMA_NAME])
    cursor.execute("CREATE INDEX sector_index ON unit.sectors USING GIST"
                   "(wkt gist_geometry_ops_nd);", schema_name)


def load_user_airspace(user_sectors_file, context, connection):
    """
    Loads a file of user defined sectors, a mix of polygons and
    cylinders.
    """
    if user_sectors_file:
        log.info(f"Loading the user sectors data table using file : {user_sectors_file}")
        try:
            airspace_source = read_sectors(user_sectors_file)
            # Drop the title row
            next(airspace_source)
            count = 0
            bad_records = []
            for airspace in airspace_source:
                if add_user_sector(airspace, context, connection)[0]:
                    count += 1
                else:
                    bad_records.append(airspace)
            log.info('Made ' + str(count) + ' user defined airspace entries')
            log.info('Failed to make ' + str(len(bad_records)) + ' user defined airspace entries')
            if len(bad_records) > 0:
                log.debug("Bad records list:")
                [log.debug(bad_record) for bad_record in bad_records]
            return True
        except Exception:
            log.exception("Failed to read user defined sector file : " + user_sectors_file +
                          " either the file or the directory does not exist.")
            return False
    else:
        log.info("No user defined sectors file provided")
        return False


def load_airspace(sectors_file, context, connection):
    """
    Load the sectors file if found else return False.
    """
    if sectors_file:
        log.info(f"Loading the sectors data table using file : {sectors_file}")
        try:
            airspace_source = read_sectors(sectors_file)
            count = 0
            bad_records = []
            for airspace in airspace_source:
                if add_airspace_geometry(airspace, context, connection):
                    count += 1
                else:
                    bad_records.append(airspace)
            log.info('Made ' + str(count) + ' airspace entries')
            log.info('Failed to make ' + str(len(bad_records)) + ' airspace entries')
            if len(bad_records) > 0:
                log.debug("Bad records list:")
                [log.debug(bad_record) for bad_record in bad_records]
            return True
        except Exception:
            log.exception("Failed to read sector init file : " + sectors_file +
                          " either the file or the directory does not exist.")
            return False
    else:
        log.info("No sectors file provided")
        return False


def load_airports(airports_file, context, connection):
    """
    Load airports file if found else return False
    """
    if airports_file:
        log.info(f"Loading the airports data table using file : {airports_file}")
        try:
            airports_source = read_airports_records(airports_file)
            count = 0
            bad_records = []
            for airport in airports_source:
                if add_airport(airport, context, connection):
                    count += 1
                else:
                    bad_records.append(airport)
            log.info('Made ' + str(count) + ' airport entries')
            log.info('Failed to make ' + str(len(bad_records)) + ' airport entries')
            if len(bad_records) > 0:
                log.debug("Bad records list:")
                [log.debug(bad_record) for bad_record in bad_records]
            return True
        except Exception:
            log.exception("Failed to read airports init file : " + airports_file +
                          " either the file or the directory does not exist.")
            return False
    return True


def create():
    """
    Creates the geo database tables.
    """
    context = ctx.CONTEXT
    postgres_admin_connection = ctx.get_connection(context, ctx.POSTGRES_DB)
    log.info("Making the db spatial")
    db_spatial_ok = make_db_spatial(context, postgres_admin_connection)
    log.info("Creating the airspace tables")
    airspace_table_ok = create_airspace_table(context, postgres_admin_connection)
    custom_airspace_table_ok = create_user_sector_table(context, postgres_admin_connection)
    airports_table_ok = create_airports_table(context, postgres_admin_connection)
    postgres_admin_connection.close()
    return db_spatial_ok and custom_airspace_table_ok and airports_table_ok and airspace_table_ok
