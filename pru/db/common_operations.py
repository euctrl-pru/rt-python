#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
Common operations across stored data types
"""
import pru.db.context as ctx

# NM to metres conversion
NM_CONVERSION_TO_M = 1852


def get_geo_db_connection():
    """
    Get the user geo database connection.  Connection for use by
    application code.

    returns a connection.
    """
    return ctx.get_connection(ctx.CONTEXT, ctx.DB_USER)


def get_ref_db_connection():
    """
    Get the user ref database connection.  Connection for use by
    application code.

    returns a connection.
    """
    return ctx.get_connection(ctx.CONTEXT, ctx.REF_DB_USER)


def create_buffer(lon, lat, radius, connection):
    """
    Given a lon and lat describing a position create a buffer with radius
    around the positiomn.
    """
    cursor = connection.cursor()
    query = "SELECT ST_AsText(ST_Buffer(ST_Point(%s, %s)::geography, %s));"
    cursor.execute(query, (lon, lat, radius))
    return cursor.fetchone()
