#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
Operations related exclusively to user defined sectors
"""
from psycopg2.extensions import AsIs
from psycopg2.extras import DictCursor
from pru.logger import logger
import pru.db.context as ctx
from pru.db.common_operations import get_geo_db_connection

log = logger(__name__)


def extract_intersection_wkts(intersection):
    """
    Given a intersection dict return the segment wkts
    """
    return intersection['segmentStrings'][0][0]


def finder(key_name, id_value):
    """
    Find the user sector with the given id value using the provided key name.
    Returns a tuple of (True, [(db_id, iata, icao, is_ct_code, lat, lon), ...])
    or (False, [])

    For example finder('id', 22) find user sector with db id 22
    """
    connection = get_geo_db_connection()
    context = ctx.CONTEXT
    schema = context[ctx.SCHEMA_NAME]
    query = "SELECT * from %s.user_defined_sectors where %s = %s;"
    params = (AsIs(schema), AsIs(key_name), id_value)
    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            formated_result = [{'id': result[0],
                                'org_id': result[1],
                                'user_id': result[2],
                                'sector_name': result[3],
                                'latitude': result[4],
                                'longitude': result[5],
                                'radius': result[6],
                                'min_altitude': result[7],
                                'max_altitude': result[8],
                                'is_cylinder': result[9],
                                'wkt': result[10]} for result in results]
            return [(False, []), (True, formated_result)][len(results) > 0]
    except Exception:
        log.exception(f"Error trying to find value {id_value} in column "
                      f"{key_name} in table {schema}.user_defined_sectors")
        return False, []


def find_by_org_user_name(org, user, name):
    """
    Find the user sector with the given id value using the provided key name.
    Returns a tuple of (True, [(db_id, iata, icao, is_ct_code, lat, lon), ...])
    or (False, [])

    For example finder('id', 22) find user sector with db id 22
    """
    connection = get_geo_db_connection()
    context = ctx.CONTEXT
    schema = context[ctx.SCHEMA_NAME]
    query = "SELECT * from %s.user_defined_sectors where org_id = %s and user_id %s and sector_name = %s;"
    params = (AsIs(schema), AsIs(org), AsIs(user), AsIs(name))
    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            formated_result = [{'db_id': result[0],
                                'org_id': result[1],
                                'user_id': result[2],
                                'sector_name': result[3],
                                'latitude': result[4],
                                'longitude': result[5],
                                'radius': result[6],
                                'min_altitude': result[7],
                                'max_altitude': result[8],
                                'is_cylinder': result[9],
                                'wkt': result[10]} for result in results]
            return [(False, []), (True, formated_result)][len(results) > 0]
    except Exception:
        log.exception(f"Error trying to find user sector with ids {org}, {user},"
                      f"{name} in table {schema}.user_defined_sectors")
        return False, []
