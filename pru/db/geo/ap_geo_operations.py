#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
Operations related to airports and airport cylinders.
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
    Find the airport with the given id value using the provided key name.
    Returns a tuple of (True, [(db_id, iata, icao, is_ct_code, lat, lon), ...])
    or (False, []).  If a record is found but the field is missing it will be
    None in the result.
    """
    connection = get_geo_db_connection()
    context = ctx.CONTEXT
    schema = context[ctx.SCHEMA_NAME]
    query = "SELECT * from %s.airports where %s = %s;"
    params = (AsIs(schema), AsIs(key_name), id_value)
    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            formated_result = [{'db_id': result[0],
                                'iata_ap_code': result[1],
                                'icao_ap_code': result[2],
                                'iso_ct_code': result[3], 'latitude': result[4],
                                'longitude': result[5]} for result in results]
            return [(False, []), (True, formated_result)][len(results) > 0]
    except Exception:
        log.exception("Error trying to find value %s in column %s in table %s.airports", id_value, key_name, schema)
        return False, []
