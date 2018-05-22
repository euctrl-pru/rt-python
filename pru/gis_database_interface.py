# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
GIS Database intersection functions.
"""
from functools import reduce
import pru.logger as logger
from pru.db.geo.geo_operations import make_augmented_points_from_positions, make_geographic_trajectory
from pru.db.geo.geo_operations import make_augmented_trajectory, find_intersections
from pru.db.geo.geo_operations import create_intersection_data_structure
from pru.db.common_operations import get_geo_db_connection, create_buffer, NM_CONVERSION_TO_M
from pru.db.geo.geo_operations import extract_details_from_intersection, find_line_poly_intersection_with_boundary, merge_l_t
from pru.db.geo.ap_geo_operations import extract_intersection_wkts
from pru.db.geo.ap_geo_operations import finder as airport_finder
from pru.db.geo.user_geo_operations import finder as user_sector_finder


log = logger.logger(__name__)


def find_2D_airspace_intersections(flight_id, latitudes, longitudes,
                                   min_altitude, max_altitude):
    """
    Find 2D airspace sector intersections.

    Note: the latitudes and longitudes arrays must be the same length, 2 positions or longer.

    Parameters
    ----------
    flight_id: string
        The flight id used for logging.

    latitudes: a numpy array of floats
        Position latitudes in [degrees].

    longitudes: a numpy array of floats
        Position longitudes in [degrees].

    min_altitude: float
        The minimum altitude of the positions [feet].

    max_altitude: float
        The maximum altitude of the positions [feet].

    Returns
    -------
    intersection_latitudes: a list of floats
        Intersection position latitudes in [degrees].

    intersection_longitudes: a list of floats
        Intersection position longitudes in [degrees].

    intersection_sector_ids : a list of strings
        The ids of the intersected sectors.

    The lists are ordered together, so the same points are at the same index.
    E.g.
    [latitudes[0], latitudes[-1]], [longitudes[0], longitudes[-1]], ['A', 'A']
    """
    log.debug("Finding intersections for flight %s, with min altitude %s and max altitude %s",
              flight_id, min_altitude, max_altitude)

    # Get the connection string
    connection = get_geo_db_connection()

    # Make a list of augmented points
    augmented_points = make_augmented_points_from_positions(
        latitudes, longitudes, flight_id, connection)

    # Convert the points to a geographic feature
    geographic_trajectory = make_geographic_trajectory(augmented_points, flight_id, connection)

    # Make a trajectory that contains the geo line, the augmented points and the 2D intersected sectors
    augmented_trajectory = make_augmented_trajectory(
        augmented_points, geographic_trajectory, flight_id, connection)

    # Find the 2D intersections
    intersections = find_intersections(
        augmented_trajectory, min_altitude, max_altitude, flight_id, connection)

    # Organise the outputs
    intersection_data_structure = create_intersection_data_structure(intersections, flight_id)

    log.debug("Completed finding intersections for flight id %s", flight_id)
    return intersection_data_structure


def find_airport_cylinder_intersection(flight_id, latitudes, longitudes,
                                       airport_id, radius, is_destination):
    """
    Find an airport cylinder intersection.

    Note: the latitudes and longitudes arrays must be the same length, 2 positions or longer.

    Parameters
    ----------
    flight_id: string
        The flight id used for logging.

    latitudes: a numpy array of floats
        Position latitudes in [degrees].

    longitudes: a numpy array of floats
        Position longitudes in [degrees].

    airport_id: string
        The ICAO id of the airport.

    radius: float
        The radius of the airport cylinder [Nautical Miles].

    is_destination: bool
        True if the airport is a destination, False if it's a departure.

    Returns
    -------
        A tuple of:
        - found: True if the intersection was found, False otherwise
        - latitude: the intersection position latitude in [degrees]
        - longitude: the intersection position longitude in [degrees]

    E.g.
    True, latitudes[0], longitudes[0]
    """
    log.debug("Finding intersection for flight %s, with airport %s at radius %s",
              flight_id, airport_id, radius)

    radius_m = radius * NM_CONVERSION_TO_M

    # Get the connection string
    connection = get_geo_db_connection()

    # Find the airport
    found = airport_finder("icao_ap_code", airport_id)
    if found[0]:
        airport = found[1][0]
        airport_lon = airport['longitude']
        airport_lat = airport['latitude']

        # Make a list of augmented points
        augmented_points = make_augmented_points_from_positions(
            latitudes, longitudes, flight_id, connection)

        # Convert the points to a geographic feature
        geographic_trajectory = make_geographic_trajectory(augmented_points, flight_id, connection)

        # Make the buffer
        buffer = create_buffer(airport_lon, airport_lat, radius_m, connection)

        # The intersections between path and buffer
        intersections = find_line_poly_intersection_with_boundary(
            geographic_trajectory, buffer, connection)

        # Organise the outputs
        intersection_wkts = extract_intersection_wkts(intersections)
        intersection_details = extract_details_from_intersection("", intersection_wkts, flight_id)

        if len(intersection_details) > 0:
            x_y_sector_ids = reduce(merge_l_t, [intersection_details], [[], [], []])

            return x_y_sector_ids[0], x_y_sector_ids[1]
        else:
            return [], []
    else:
        return [], []


def find_2D_user_airspace_intersections(flight_id, latitudes, longitudes,
                                        min_altitude, max_altitude):
    """
    Find 2D user airspace intersections.

    Note: the latitudes and longitudes arrays must be the same length, 2 positions or longer.

    Parameters
    ----------
    flight_id: string
        The flight id used for logging.

    latitudes: a numpy array of floats
        Position latitudes in [degrees].

    longitudes: a numpy array of floats
        Position longitudes in [degrees].

    min_altitude: float
        The minimum altitude of the positions [feet].

    max_altitude: float
        The maximum altitude of the positions [feet].

    Returns
    -------
    intersection_latitudes: a list of floats
        Intersection position latitudes in [degrees].

    intersection_longitudes: a list of floats
        Intersection position longitudes in [degrees].

    intersection_sector_ids : a list of strings
        The ids of the intersected sectors.

    The lists are ordered together, so the same points are at the same index.
    E.g.
    [latitudes[0], latitudes[-1]], [longitudes[0], longitudes[-1]], ['A', 'A']
    """
    log.debug("Finding intersections for flight %s, with min altitude %s and max altitude %s",
              flight_id, min_altitude, max_altitude)

    # Get the connection string
    connection = get_geo_db_connection()

    # Make a list of augmented points
    augmented_points = make_augmented_points_from_positions(
        latitudes, longitudes, flight_id, connection)
    # Convert the points to a geographic feature
    geographic_trajectory = make_geographic_trajectory(augmented_points, flight_id, connection)

    # Make a trajectory that contains the geo line, the augmented points and
    # the 2D user defined intersected sectors
    augmented_trajectory = make_augmented_trajectory(
        augmented_points, geographic_trajectory, flight_id, connection, True)

    # Find the 2D intersections
    intersections = find_intersections(
        augmented_trajectory, min_altitude, max_altitude, flight_id, connection)
    # Organise the outputs
    intersection_data_structure = create_intersection_data_structure(intersections, flight_id)

    log.debug("Completed finding intersections with user defined sectors for flight id %s", flight_id)
    return intersection_data_structure


def find_user_sector_altitude_range(db_id):
    """
    Find the user defined sector for the given database id.
    The db id will be unique for each entry, there is only one
    possible row that can be found.

    Requires a database identifier integre as a string.

    Returns a tuple of (True, res_dict) or
    (False, {})
    """
    found = user_sector_finder("id", db_id)
    if found[0]:
        res = found[1][0]
        return True, {'id': res['id'],
                      'min_altitude': res['min_altitude'],
                      'max_altitude': res['max_altitude'],
                      'is_cylinder': res['is_cylinder']}
    else:
        return False, {}
