#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
Administration operations for the geo db.
"""

import os
import socket
import time
from pru.db.geo.geo_init import load_airspace, remove_all_sectors, tear_down
from pru.db.geo.geo_init import load_airports, remove_all_airports
from pru.db.geo.geo_init import load_user_airspace, remove_all_user_defined_sectors
from pru.db.common_init import create as create_db, DB_TYPE_GEO
from pru.db.geo.geo_init import create as create_geo_db
from pru.logger import logger
import pru.db.context as ctx

log = logger(__name__)


def remove_geo_db():
    """
    Remove the db
    """
    remove_all_sectors()
    remove_all_airports()
    remove_all_user_defined_sectors()
    tear_down()


def create_geo_database():
    """
    Create a geo db.
    """
    log.info("Starting to create the geo db")
    log.info("Waiting for the database to be ready")
    log.info(f"Testing connection on host: {ctx.geo_db_hostname} and port {ctx.geo_db_port}")

    # We need to sleep and retry ubtil the db wakes up
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((ctx.geo_db_hostname, int(ctx.geo_db_port)))
            s.close()
            break
        except socket.error as ex:
            log.debug("Database not ready..")
            time.sleep(5)  # 5 seconds between tests
    log.info("Geo database is now ready.")
    if create_db(DB_TYPE_GEO):
        if create_geo_db():
            log.info("Geo database creation is complete.")
            return True
        else:
            log.info("Failed to make the airspace db, could not create the tables.")
    else:
        log.info("Failed to make the airspace db, could not create the database.")


def initialise_airspace(sector_file_path, reset=False):
    """
    Uses the provided file path to load the sectors file,
    may be csv or geojson.
    If no sectors file is found we return false.

    Reset=True  Remove all and replace with this file.
    Reset=False Add these sectors to the sectors table.  Note,
                this is not an update.

    return  True if we succeeded
            A tuple of (False, message) if we fail

    """
    connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
    context = ctx.CONTEXT
    if os.path.exists(sector_file_path):
        if reset:
            remove_all_sectors()
        load_airspace(sector_file_path, context, connection)
        return True
    else:
        return (False, "Path not found " + sector_file_path)


def initialise_airports(airports_file_path, reset=False):
    """
    Uses the provided file path to load an airports file,
    must be csv.
    If no airports file is found we return false.

    Reset=True  Remove all and replace with this file.
    Reset=False Add these airports to the sectors table.  Note,
                this is not an update.

    return  True if we succeeded
            A tuple of (False, message) if we fail
    """
    connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
    context = ctx.CONTEXT
    if os.path.exists(airports_file_path):
        if reset:
            remove_all_airports()
        load_airports(airports_file_path, context, connection)
        return True
    else:
        return (False, "Path not found " + airports_file_path)


def initialise_user_airspace(user_sector_file_path, reset=False):
    """
    Uses the provided file path to load the users sectors file,
    may be csv or geojson.
    If no sectors file is found we return false.

    Reset=True  Remove all and replace with this file.
    Reset=False Add these sectors to the user sectors table.  Note,
                this is not an update.

    return  True if we succeeded
            A tuple of (False, message) if we fail

    """
    connection = ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)
    context = ctx.CONTEXT
    if os.path.exists(user_sector_file_path):
        if reset:
            remove_all_user_defined_sectors()
        load_user_airspace(user_sector_file_path, context, connection)
        return True
    else:
        return (False, "Path not found " + user_sector_file_path)
