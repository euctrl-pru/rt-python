#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
# Common database inititialisation code.  These functions are used to
# initialise both the reference and the geo databases.
#
"""
Common initialisation code.  Apllies to all system databses.
"""
from pru.logger import logger
import pru.db.context as ctx
from psycopg2.extensions import AsIs
from psycopg2 import ProgrammingError, Error


log = logger(__name__)

# The supported DB types
DB_TYPE_GEO = "geo"
DB_TYPE_REF = "ref"
DB_TYPES = {DB_TYPE_GEO, DB_TYPE_REF}


def create_users_roles(context, connection):
    """
    Creates the user roles applicable for the schema.
    """
    admin_name = context[ctx.ADMIN_NAME]
    user_name = context[ctx.USER_NAME]
    query_admin = "CREATE ROLE %s with CREATEDB CREATEROLE LOGIN PASSWORD '%s';"
    params_admin = [AsIs(admin_name), AsIs(admin_name)]
    return_state = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(query_admin, params_admin)
    except ProgrammingError:
        log.warning(f"Failed to add role {admin_name} going to "
                    "re-use this role.")
        return_state = False
    query_user = "CREATE ROLE %s with LOGIN;"
    params_user = [AsIs(user_name)]
    try:
        with connection.cursor() as cursor:
            cursor.execute(query_user, params_user)
    except ProgrammingError:
        log.warning(f"Failed to add role {user_name} Going to reuse "
                    "this role.")
        return_state = False
    return return_state


def create_db(context, connection):
    """
    Creates the database as defined in the context.
    """
    admin_role = context[ctx.ADMIN_NAME]
    db_name = context[ctx.DB_NAME]
    cursor = connection.cursor()
    query = "CREATE DATABASE  %s with owner = %s;"
    params = (AsIs(db_name), AsIs(admin_role))
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
    except ProgrammingError:
        log.exception("Failed to make database.")
        return False
    return True


def create_db_schema(context, connection):
    """
    Makes the databse schema for the given context.
    """
    admin_name = context[ctx.ADMIN_NAME]
    user_name = context[ctx.USER_NAME]
    schema_name = context[ctx.SCHEMA_NAME]
    log.info(f"Creating the schema space {schema_name}")
    query = "CREATE SCHEMA IF NOT EXISTS %s AUTHORIZATION %s;"
    params = [AsIs(schema_name), AsIs(admin_name)]
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            cursor.execute("GRANT USAGE ON SCHEMA %s TO %s;",
                           [AsIs(schema_name), AsIs(user_name)])
    except Error:
        log.exception("Failed to create the db schema.")
        return False
    return True


def create(db_type=DB_TYPE_GEO):
    """
    Creates the database users, schema and database.
    The flag type determines geo or ref.
    db_type one of the supported db types above.

    returns True if the create succeeded.

    """
    if DB_TYPES.__contains__(db_type):
        log.info(f"Creating users, db and schema for db type {db_type}.")
        context = ctx.CONTEXT
        if db_type == DB_TYPE_REF:
            postgres_connection = ctx.get_connection(context, ctx.REF_POSTGRES)
        else:
            postgres_connection = ctx.get_connection(context, ctx.POSTGRES)
        log.info(f"Creating the user roles for db type {db_type}.")
        roles_ok = create_users_roles(context, postgres_connection)
        log.info(f"Creating the database instance for db {db_type}.")
        db_ok = create_db(context, postgres_connection)
        log.info(f"Creating the database schema for db {db_type}.")
        postgres_connection.close()
        if db_type == DB_TYPE_REF:
            postgres_db_connection = ctx.get_connection(context, ctx.REF_POSTGRES_DB)
        else:
            postgres_db_connection = ctx.get_connection(context, ctx.POSTGRES_DB)
        schema_ok = create_db_schema(context, postgres_db_connection)
        postgres_db_connection.close()
        log.info(f"Completed creating the database for db {db_type}.")
        return roles_ok and db_ok and schema_ok
    else:
        log.error(f"Unknown database type, {db_type}, should be one of {DB_TYPES}.")
        return False
