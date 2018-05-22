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


def find_sectors_intersected_by(line_string, flight_id, context, connection):
    """
    Lists the airspace ids and details of those airspaces where the
    given line string intersects.
    """
    log.debug(f"Finding trajectory intersection with airspaces for flight id: {flight_id}")
    schema_name = context[ctx.SCHEMA_NAME]
    try:
        with connection.cursor() as cursor:
            query = "SELECT id, av_airspace_id, min_altitude, max_altitude " \
                    "from %s.sectors where ST_Intersects(wkt, ST_GeographyFromText('SRID=4326;%s'));"
            params = [AsIs(schema_name), AsIs(line_string)]
            cursor.execute(query, params)
            return cursor.fetchall()
    except InternalError:
        log.exception(f"Failed whist trying to find the intersection between "
                      "a route with flight id {flight_id} and the airspace model.")
        return []


def find_user_sectors_intersected_by(line_string, flight_id, context, connection):
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
                    "ST_Intersects(wkt, ST_GeographyFromText('SRID=4326;%s'));"
            params = [AsIs(schema_name), AsIs(line_string)]
            cursor.execute(query, params)
            return cursor.fetchall()
    except InternalError:
        log.exception(f"Failed whist trying to find the intersection between "
                      "a route with flight id {flight_id} and the airspace model.")
        return []


def find_high_sectors(sectors, max_altitude):
    """
    Finds sectors that are above the max altitude of the trajectory.
    """
    return [sector for sector in sectors if int(sector[2]) > max_altitude]


def find_low_sectors(sectors, min_altitude):
    """
    Finds sectors that are below the min altitude of the trajectory.
    """
    return [sector for sector in sectors if int(sector[3]) < min_altitude]


def remove_sectors(sectors, sector_list):
    """
    Remove sectors from sector list.
    """
    return list(filterfalse(set(sectors).__contains__,
                            sector_list))


def eliminate_sectors(augmented_trajectory, min_altitude, max_altitude, flight_id):
    """
    Modifies the given extended trajectory by eliminating sectors that
    the trajectory cannot intersect.
    1/ Sectors whose max altitude is below the min altitude of the trajectory.
    2/ Sectors whose min altitude is above the max altitude of the trajectory.

    augmented_trajectory The trajectory augmented with sectors.
    min_altitude The min altitude of the trajectory in feet
    max_altitude The max altitude of the trajectory in feet

    returns the augmented trajectory with the intersected sector list reduced
    by the elimination.

    """
    log.debug(f"Eliminate sectors for flight_id: {flight_id}")
    sectors = augmented_trajectory['sectors']
    sectors_remaining = remove_sectors(find_high_sectors(sectors, max_altitude), sectors)
    sector_count = len(sectors_remaining)
    log.debug("Removed %s high sectors", str(len(sectors) - sector_count))
    log.debug("Removed high sectors leaving %s", str(len(sectors_remaining)))
    sectors_remaining = remove_sectors(find_low_sectors(sectors_remaining, min_altitude), sectors_remaining)
    log.debug("Removed %s low sectors", str(sector_count - len(sectors_remaining)))
    log.debug("%s sectors remaining", str(len(sectors_remaining)))
    augmented_trajectory['sectors'] = sectors_remaining
    return augmented_trajectory


def make_geographic_trajectory(augmented_points, flight_id, connection):
    """
    Given a list of augmented points create a geographic line segment.
    """
    log.debug(f"Making geo trajectory for flight id: {flight_id}")
    return make_line_from_augmented_points(
            extract_point_list_from_augmented_points(augmented_points),
            flight_id,
            connection)[0]


def make_augmented_trajectory(augmented_points, geographic_trajectory, flight_id, connection, is_user_defined=False):
    """
    """
    log.debug(f"Creating an augmented trajectory for flight id: {flight_id}")
    if not is_user_defined:
        sectors = find_sectors_intersected_by(geographic_trajectory, flight_id, ctx.CONTEXT, connection)
    else:
        sectors = find_user_sectors_intersected_by(geographic_trajectory, flight_id, ctx.CONTEXT, connection)
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
    Finds an aairspace with the given id, for example
    LFBBT2. Returns a list, list may be empty.
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


def find_line_poly_intersection_with_boundary(lineString, polygonString, connection):
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


def find_intersections(augmented_trajectory, min_altitude, max_altitude, flight_id, connection):
    """
    Finds the points on the trajectory that intersect with the sectors of the
    the augmented trajectory.
    """
    log.debug(f"Finding intersection for flight id {flight_id}")
    # Eliminate sectors that are below and above the min and max altitude of
    # the trajectory.
    is_user_defined = augmented_trajectory['is_user_defined']
    reduced_trajectory = eliminate_sectors(augmented_trajectory, min_altitude, max_altitude, flight_id)

    # Find each sector
    sector_IDs = [sector[0] for sector in reduced_trajectory['sectors']]
    log.debug("Found sector ids %s", str(sector_IDs))
    sectors = [find_airspace_by_database_ID(str(sector_id),
                                            ctx.CONTEXT,
                                            connection, is_user_defined)[0] for sector_id in sector_IDs]
    # Find the points of the trajectory where the trajectory intersects
    # with each sector
    if is_user_defined:
        segments = [{'flight_id': reduced_trajectory['extendedPoints'][0]['flight_id'],
                     'intersections': find_line_poly_intersection_with_boundary(reduced_trajectory['line'],
                                                                                sector['wkt'],
                                                                                connection),
                     'sector_id': sector['id'],
                     'org_id': sector['org_id'],
                     'user_id': sector['user_id'],
                     'sector_name': sector['sector_name'],
                     'min_altitude': sector['min_altitude'],
                     'max_altitude': sector['max_altitude'],
                     'is_cylinder': sector['is_cylinder'],
                     'is_user_defined': is_user_defined} for sector in sectors]
    else:
        segments = [{'flight_id': reduced_trajectory['extendedPoints'][0]['flight_id'],
                     'intersections': find_line_poly_intersection_with_boundary(reduced_trajectory['line'],
                                                                                sector['wkt'],
                                                                                connection),
                     'sector_id': sector['id'],
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


def extract_details_from_intersection(sector_id, wkt, flight_id):
    """
    Given an intersection wkt use shapley to create the point or multipoint
    object.  Then extract the latitude and longitudes from the (multi)point.

    Returns a list of tuples of sector_id, latiitude and longitude
    """
    return extract(sector_id, loads(wkt), flight_id)


def make_sector_description(intersection):
    """
    Makes a text descritption of the sector from the database row for the
    sector.
    Returns a string created like dbid-av_airspace_id-av_icao_state_id-av_name
    """
    if intersection['is_user_defined']:
        return f'{intersection["sector_id"]}'
    else:
        return f'{intersection["av_icao_state_id"]}/{intersection["av_name"]}/{intersection["sector_id"]}/{intersection["av_airspace_id"]}'


def extract_intersection_wkts(intersections):
    """
    Given a list of intersection dicts return a list of wkts with sector
    descriptive text as a tuple.  ie ("some-text-made-from-sector-ids", wkt)
    """
    return [(make_sector_description(intersection), intersection['intersections']['segmentStrings'][0][0]) for intersection in intersections]


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
    # The intersection wkts are tuples of the sector_id and the wkt for the
    # intersection.
    intersection_wkts = extract_intersection_wkts(intersections)
    intersection_details = [extract_details_from_intersection(*intersection_wkt, flight_id) for intersection_wkt in intersection_wkts]
    x_y_sector_ids = reduce(merge_l_t, intersection_details, [[], [], []])
    return x_y_sector_ids[0], x_y_sector_ids[1], x_y_sector_ids[2]
