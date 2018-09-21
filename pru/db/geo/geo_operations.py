#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#

"""
operations related to airspaces and intersections.
"""

from psycopg2 import Error, InternalError
from psycopg2.extensions import AsIs
from psycopg2.extras import DictCursor
from itertools import filterfalse
from functools import reduce
from shapely.wkt import loads
import pru.db.context as ctx
from pru.logger import logger

log = logger(__name__)


def make_point(lon, lat, connection):
    """
    Makes a geo point
    """
    cursor = connection.cursor()
    query = "SELECT ST_MakePoint(%s, %s)"
    params = (float(lon), float(lat))
    cursor.execute(query, params)
    return cursor.fetchone()


def make_augmented_point_from_position(position, flight_id, connection):
    """
    Takes a position tuple and makes a augmented point.
    """
    point = make_point(position[1], position[0], connection)
    return {'flight_id': flight_id, 'lon': position[1], 'lat': position[0],
            'geoPoint': point}


def make_augmented_points_from_positions(latitudes, longitudes, flight_id, connection):
    """
    Takes a list of latitudes and a list of longitudes and a flight_id.
    Makes a list of augmented points.
    """
    return [make_augmented_point_from_position(position, flight_id, connection) for position in zip(latitudes, longitudes)]


def extract_point_list_from_augmented_points(augmented_points):
    """
    Given a list or generator of augmented points extract the geo point
    representation as a list.
    """
    return list(map(lambda augmented_points: augmented_points['geoPoint'],
                    augmented_points))


def make_line_from_augmented_points(augmented_points, flight_id, connection):
    """
    Given a list of augmented points create a geographic line.
    """
    if (len(augmented_points) == 0):
        log.warning(f"Creating a line from a list of points but the list "
                    "was empty for flight id {flight_id}.")
        return [[]]
    cursor = connection.cursor()
    query = "SELECT ST_AsEWKT(ST_MakeLine(ARRAY[%s]));"
    params = [augmented_points]
    cursor.execute(query, params)
    return cursor.fetchone()


def find_sectors_intersected_by(line_string, flight_id, min_altitude, max_altitude, context, connection):
    """
    Lists the airspace ids and details of those airspaces where the
    given line string intersects excluding those that are outside of the range of
    altitudes of the trajectory.
    """
    log.debug(f"Finding trajectory intersection with airspaces for flight id: {flight_id}")
    schema_name = context[ctx.SCHEMA_NAME]
    try:
        with connection.cursor() as cursor:
            query = "SELECT id, av_airspace_id, min_altitude, max_altitude " \
                    "from %s.sectors where " \
                    "NOT (max_altitude < %s OR min_altitude > %s) AND " \
                    "ST_Intersects(wkt, ST_GeographyFromText('SRID=4326;%s'));"
            params = [AsIs(schema_name), min_altitude,  max_altitude, AsIs(line_string)]
            cursor.execute(query, params)
            return cursor.fetchall()
    except InternalError:
        log.exception(f"Failed whist trying to find the intersection between "
                      "a route with flight id {flight_id} and the airspace model.")
        return []


def find_user_sectors_intersected_by(line_string, flight_id, min_altitude, max_altitude, context, connection):
    """
    Lists the user defined airspace uids and details of those airspaces where the
    given line string intersects.
    """
    log.debug(f"Finding trajectory intersection with user defined airspaces for flight id: {flight_id}")
    schema_name = context[ctx.SCHEMA_NAME]
    try:
        with connection.cursor() as cursor:
            query = "SELECT id, org_id, min_altitude, max_altitude, user_id, " \
                    "sector_name from %s.user_defined_sectors where " \
                    "NOT (max_altitude < %s OR min_altitude > %s) AND " \
                    "ST_Intersects(wkt, ST_GeographyFromText('SRID=4326;%s'));"
            params = [AsIs(schema_name), min_altitude,  max_altitude, AsIs(line_string)]
            cursor.execute(query, params)
            return cursor.fetchall()
    except InternalError:
        log.exception(f"Failed whist trying to find the intersection between "
                      "a route with flight id {flight_id} and the airspace model.")
        return []


def make_geographic_trajectory(augmented_points, flight_id, connection):
    """
    Given a list of augmented points create a geographic line segment.
    """
    log.debug(f"Making geo trajectory for flight id: {flight_id}")
    return make_line_from_augmented_points(
            extract_point_list_from_augmented_points(augmented_points),
            flight_id,
            connection)[0]


def make_augmented_trajectory(augmented_points, geographic_trajectory, flight_id, min_altitude, max_altitude, connection, is_user_defined=False):
    """
    Makes a trajectory augmented with geographic positions and a list of sectors
    intersected by the trajectory excluding those that do not meet the altitude range
    of the trajectory.
    """
    log.debug(f"Creating an augmented trajectory for flight id: {flight_id}")
    if not is_user_defined:
        sectors = find_sectors_intersected_by(geographic_trajectory, flight_id, min_altitude, max_altitude, ctx.CONTEXT, connection)
    else:
        sectors = find_user_sectors_intersected_by(geographic_trajectory, flight_id, min_altitude, max_altitude, ctx.CONTEXT,  connection)
    return {'extendedPoints': augmented_points,
            'line': geographic_trajectory,
            'sectors': sectors,
            'is_user_defined': is_user_defined}


def find_sector(db_ID, connection):
    schemaName = ctx.CONTEXT[ctx.SCHEMA_NAME]
    with connection.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("SELECT id, av_airspace_id, av_icao_state_id, av_name, min_altitude, max_altitude FROM %s.sectors WHERE "
                       "id = %s",
                       [AsIs(schemaName), db_ID])
        return cursor.fetchone()


def find_sector_identifiers(db_ID, context, connection):
    """
    Finds the identifiers for a sector given the db id of the sector.
    """
    schemaName = context[ctx.SCHEMA_NAME]
    with connection.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("SELECT av_airspace_id, av_icao_state_id, av_name FROM %s.sectors WHERE "
                       "id = %s",
                       [AsIs(schemaName), db_ID])
        return cursor.fetchmany()


def find_airspace_by_database_ID(db_ID, context, connection, is_user_defined=False):
    """
    Finds an aairspace with the given database id
    Returns a list, list may be empty.
    """
    schemaName = context[ctx.SCHEMA_NAME]
    with connection.cursor(cursor_factory=DictCursor) as cursor:
        if is_user_defined:
            cursor.execute("SELECT * FROM %s.user_defined_sectors WHERE "
                           "id = %s", [AsIs(schemaName), db_ID])
            return cursor.fetchmany()
        else:
            cursor.execute("SELECT * FROM %s.sectors WHERE "
                           "id = %s", [AsIs(schemaName), db_ID])
            return cursor.fetchmany()


def originates(first_point, polygon_string, flight_id, sector_id, connection):
    """
    If the first point is inside the given sector we determine that the
    trajectory originates in the sector.
    first_point wkb for the first point of the trajectory
    returns True => originates in sectors
    """
    cursor = connection.cursor()
    query = "SELECT ST_Intersects(%s::geography, %s::geography);"
    params = [first_point, polygon_string]
    cursor.execute(query, params)
    originates = cursor.fetchone()[0]
    if originates:
        log.debug(f"Flight with  id {flight_id} originates in sector {sector_id}")
    return originates


def find_line_poly_intersection_without_boundary(lineString, polygonString, connection):
    """
    Use the geo db to find the intersections between the linestring and the unbounded polygon string.
    The polygon is assumed to _NOT_ have a boundary around it.
    """
    query = "SELECT ST_AsText(ST_Intersection(%s::geography, ST_Force2D(ST_Boundary(%s))::geography));"
    params = [lineString, polygonString]
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            res = cursor.fetchall()
            return {'segmentStrings': res,
                    'ploygonString': polygonString}
    except Error:
        log.exception("Failed to find intersection : Error")
        return []


def find_line_poly_intersection_with_boundary(lineString, polygonString, connection):
    """
    Use the geo db to find the intersections between the linestring and the bounded polygon string.
    The polygon is assumed to already have a boundary around it.
    """
    query = "SELECT unit.find_intersections(%s, %s)"
    params = [lineString, polygonString]
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            res = cursor.fetchall()
            return {'segmentStrings': res,
                    'ploygonString': polygonString}
    except Error:
        log.exception("Failed to find intersection : Error")
        return []


def find_intersections(augmented_trajectory, min_altitude, max_altitude, flight_id, connection):
    """
    Finds the points on the trajectory that intersect with the sectors of the
    the augmented trajectory.
    """
    log.debug(f"Finding intersection for flight id {flight_id}")

    first_point = augmented_trajectory['extendedPoints'][0]['geoPoint']
    first_point_lon = augmented_trajectory['extendedPoints'][0]['lon']
    first_point_lat = augmented_trajectory['extendedPoints'][0]['lat']
    is_user_defined = augmented_trajectory['is_user_defined']

    # Find each sector
    sector_IDs = [sector[0] for sector in augmented_trajectory['sectors']]
    log.debug("Found sector ids %s", str(sector_IDs))
    sectors = [find_airspace_by_database_ID(str(sector_id),
                                            ctx.CONTEXT,
                                            connection, is_user_defined)[0] for sector_id in sector_IDs]
    # Find the points of the trajectory where the trajectory intersects
    # with each sector
    if is_user_defined:
        segments = [{'flight_id': flight_id,
                     'intersections': find_line_poly_intersection_with_boundary(augmented_trajectory['line'],
                                                                                sector['bounded_sector'],
                                                                                connection),
                     'origin': {'is_origin': originates(first_point, sector['wkt'], flight_id, sector['id'], connection),
                                'origin_lat': first_point_lat,
                                'origin_lon': first_point_lon},
                     'id': sector['id'],
                     'org_id': sector['org_id'],
                     'user_id': sector['user_id'],
                     'sector_name': sector['sector_name'],
                     'min_altitude': sector['min_altitude'],
                     'max_altitude': sector['max_altitude'],
                     'is_cylinder': sector['is_cylinder'],
                     'is_user_defined': is_user_defined} for sector in sectors]
    else:
        segments = [{'flight_id': flight_id,
                     'intersections': find_line_poly_intersection_with_boundary(augmented_trajectory['line'],
                                                                                sector['bounded_sector'],
                                                                                connection),
                     'origin': {'is_origin': originates(first_point, sector['wkt'], flight_id, sector['id'], connection),
                                'origin_lat': first_point_lat,
                                'origin_lon': first_point_lon},
                     'id': sector['id'],
                     'av_icao_state_id': sector['av_icao_state_id'],
                     'av_name': sector['av_name'],
                     'av_airspace_id': sector['av_airspace_id'],
                     'min_altitude': sector['min_altitude'],
                     'max_altitude': sector['max_altitude'],
                     'is_user_defined': is_user_defined} for sector in sectors]
    return segments


def extract(sector_id, shape, flight_id):
    """
    Given a shapley shape find if we have a point or a multipoint.
    For a point extract the y, x pair as a list of one tuple of sector_id,
    latitude and longitude.
    For a multipoint return a list of multiple tuples.
    """
    if shape.geom_type == 'MultiPoint':
        return [(sector_id, p.y, p.x) for p in shape]
    elif shape.geom_type == 'Point':
        return [(sector_id, shape.y, shape.x)]
    else:
        log.debug("Unknown geom type : %s in flight id %s and sector_id %s, was %s, skipping", shape.geom_type, flight_id, sector_id, str(shape))
        return []


def extract_details_from_intersection(sector_id, wkt, origin, flight_id):
    """
    Given an intersection wkt use shapley to create the point or multipoint
    object.  Then extract the latitude and longitudes from the (multi)point.

    Returns a list of tuples of sector_id, latiitude and longitude
    """
    intersection_tuples = extract(sector_id, loads(wkt), flight_id)
    if origin['is_origin']:
        # If this sector is an origin sector, add in the lat lons at the start.
        intersection_tuples = [(sector_id, origin['origin_lat'], origin['origin_lon'])] + intersection_tuples
    return intersection_tuples


def make_sector_description(intersection, is_user_defined=False):
    """
    Makes a text description of the sector from the intersection description
    """
    if is_user_defined:
        return f'{intersection["org_id"]}/{intersection["user_id"]}/{intersection["sector_name"]}'
    else:
        return f'{intersection["av_icao_state_id"]}/{intersection["av_name"]}/{intersection["id"]}/{intersection["av_airspace_id"]}'


def make_sector_identifier(intersection):
    """
    Makes a text version of the database id in the given intersection
    """
    return f'{intersection["id"]}'


def extract_intersection_wkts(intersections):
    """
    Given a list of intersection dicts return a list of wkts with sector
    descriptive text and the origin details as a tuple.
    ie ("some-text-made-from-sector-ids", wkt, {is_origin:False, origin_lat:lat, origin_lon: lon})
    """
    return [(make_sector_identifier(intersection),
             intersection['intersections']['segmentStrings'][0][0], intersection['origin'])
            for intersection in intersections]


def merge_l_t(l, lt):
    """
    Merge a list of tuples lt, each of three values into three lists l.
    For example: [('a', 'b', 'c'), ('a', 'd', 'e')] ->
    [['a', 'a'], ['b', 'd'], ['c', 'e']]
    """
    for t in lt:
        l[0].append(t[1])
        l[1].append(t[2])
        l[2].append(t[0])
    return l


def create_intersection_data_structure(intersections, flight_id):
    """
    Given the intersection data structures create a response tuple.
    """
    # The intersection wkts are tuples of the sector_id, the wkt and the origin
    # status for the intersection.
    intersection_wkts = extract_intersection_wkts(intersections)
    intersection_details = [extract_details_from_intersection(*intersection_wkt, flight_id) for intersection_wkt in intersection_wkts]
    x_y_sector_ids = reduce(merge_l_t, intersection_details, [[], [], []])
    return x_y_sector_ids[0], x_y_sector_ids[1], x_y_sector_ids[2]
