#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
Administration operations for the ref db
"""

import os
import socket
import time
from pru.db.reference.ref_init import load_fleet_data, remove_all_reference_data, tear_down
from pru.db.common_init import create as create_db
from pru.db.common_init import DB_TYPE_REF
from pru.db.reference.ref_init import create as create_reference_db
from pru.logger import logger
import pru.db.context as ctx

log = logger(__name__)


def remove_ref_db():
    """
    Remove the reference db.
    """
    log.info("Removing the reference database")
    remove_all_reference_data()
    tear_down()
    log.info("Reference database has been removed.")


def create_ref_db():
    """
    Create a reference db.
    """
    log.info("Starting to create the reference db")
    log.info("Waiting for the database to be ready")
    log.info(f"Testing connection on host: {ctx.ref_db_hostname} and port {ctx.ref_db_port}")

    # We need to sleep and retry until the db wakes up
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect((ctx.ref_db_hostname, int(ctx.ref_db_port)))
            s.close()
            break
        except socket.error as ex:
            time.sleep(10)  # 10 seconds between tests
    log.info("Ref database is now ready.")
    if create_db(DB_TYPE_REF):
        if create_reference_db():
            log.info("Ref database creation is complete.")
            return True
        else:
            log.info("Failed to make the reference db, could not create the tables.")
            return False
    else:
        log.info("Failed to make the reference db, could not create the database.")
        return False


def initialise_fleet_data(fleet_file_path=None, reset=False):
    """
    Uses the provided file path to load the fleet file csv file.
    If no fleet file is found we return false.

    Reset=True  Remove all records and replace with this file.
    Reset=False Add these fleet entries to the fleet table.

    return  True if we succeeded
            A tuple of (False, message) if we fail

    """
    connection = ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)
    context = ctx.CONTEXT
    if os.path.exists(fleet_file_path):
        if reset:
            remove_all_reference_data()
        load_fleet_data(fleet_file_path, context, connection)
        connection.close()
        return True
    else:
        return (False, "Path not found: " + fleet_file_path)
