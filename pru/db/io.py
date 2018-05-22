# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
A python module that reads csv or geojson data files including
sectors, airports and fleet data.
"""

import csv
from pathlib import Path
from shapely.geometry import shape
import geojson


def _convert_json_coordinates(coordinates):
    """Convert a geojson expression of a sector boundary to a wkt."""
    return [shape(coordinates).wkt]


def _convert_json_properties(properties):
    """
    Convert a geojson expression of the properties of a sector into a
    list of properties. Properties are in a dictionary.

    The geojson has no object id field so we inject one.
    """
    return [properties['AC_ID'], properties['AV_AIRSPACE_ID'],
            properties['AV_ICAO_STATE_ID'], properties['MIN_FLIGHT_LEVEL'],
            properties['MAX_FLIGHT_LEVEL'], properties['AV_NAME'],
            properties['SECTOR_TYPE'], '0']


def _convert_json_custom_properties(properties):
    """
    Convert a geojson expression of the properties of a user defined sector
    into a list of properties. Properties are in a dictionary.

    """
    return [properties['ORG_ID'], properties['USER_ID'],
            properties['SECTOR_ID'], properties['LATITUDE'],
            properties['LONGITUDE'], properties['RADIUS'],
            properties['MIN_FLIGHT_LEVEL'], properties['MAX_FLIGHT_LEVEL'],
            properties['IS_CYLINDER']]


def _convert_json(properties, coordinates):
    """
    Given a geojson expression of sector properties and sector coordinates
    convert them to a list of properties with a wkt description of a boundary.

    Parameters
    ----------
    properties  The geojson properties string.
    coordinates The geojson coordinate string representing the sector shape.

    """
    return _convert_json_properties(properties) + \
        _convert_json_coordinates(coordinates)


def _convert_custom_json(properties, coordinates):
    """
    Given a geojson expression of sector properties and sector coordinates
    convert them to a list of properties with a wkt description of a boundary.

    Parameters
    ----------
    properties  The geojson properties string.
    coordinates The geojson coordinate string representing the sector shape.

    """
    return _convert_json_custom_properties(properties) + \
        _convert_json_coordinates(coordinates)


def _read_lazy_sectors_geojson(path):
    """
    Returns a generator - function is lazy.

    Given a path (as a text string) to a geojson file describing an airspace,
    reads in the file to rows of airspace definitions.  Returns a generator
    over a list of rows.

    This function is a substitute for the csv reader.

    Parameters
    ----------
    path The string path to the geojson file.

    Use in the same way as the csv reader.
    """
    with open(path) as gjs:
        # First yield the header row
        yield ['AC_ID',
               'AV_AIRSPACE_ID',
               'AV_ICAO_STATE_ID',
               'MIN_FLIGHT_LEVEL',
               'MAX_FLIGHT_LEVEL',
               'AV_NAME',
               'SECTOR_TYPE',
               'OBJECTID',
               'WKT']
        geo_json_data = geojson.load(gjs)
        for feature in geo_json_data['features']:
            yield _convert_json(feature['properties'], feature['geometry'])


def _read_lazy_custom_sectors_geojson(path):
    """
    Returns a generator - function is lazy.

    Given a path (as a text string) to a geojson file describing an airspace,
    reads in the file to rows of airspace definitions.  Returns a generator
    over a list of rows.

    This function is a substitute for the csv reader.

    Parameters
    ----------
    path The string path to the geojson file.

    Use in the same way as the csv reader.
    """
    with open(path) as gjs:
        # First yield the header row
        yield ['ORG_ID',
               'USER_ID',
               'SECTOR_ID',
               'LATITUDE',
               'LONGITUDE',
               'RADIUS',
               'MIN_FLIGHT_LEVEL',
               'MAX_FLIGHT_LEVEL',
               'IS_CYLINDER',
               'WKT']
        geo_json_data = geojson.load(gjs)
        for feature in geo_json_data['features']:
            yield _convert_json(feature['properties'], feature['geometry'])


def _read_lazy_CSV(file_path):
    """
    Returns a generator - function is lazy.

    Given a path to a csv file that has the first line as the field names,
    returns a list of dictionaries of field name to value, one dictionary
    per field, one list per row.

    Parameters
    ----------
    path The string path to the csv file.

    Example of use :

    gen = read_lazy_CSV(dataPath)
    [next(gen) for _ in range(5)]    The next five samples
    next(gen)                        The next sample
    """
    with open(file_path) as csvFile:
        reader = csv.reader(csvFile)
        for row in reader:
            yield row


def read_sectors(path):
    """
    Reads airspace sectors from the given string path, supports csv and
    geo json.

    Returns a generator if the path exists or an empty generator if the path
    is not found or the file extension is unknown.

    The first row is the header row.

    Parameters
    ----------
    path The string path to the sector file, either csv or geojson.

    If the path is not a valid file we return an empty itereator.

    Examples:

    geojson :
    json_loc = "/Users/user/Downloads/ES_428.geojson"
    sectors_j = read_sectors(json_loc)
    next(sectors_j)
    [next(sectors_j) for _ in range(3)]

    csv:
    csv_loc = "/Users/user/Public/elementary_sectors.csv"
    sectors_c = read_sectors(csv_loc)
    next(sectors_c)
    [next(sectors_c) for _ in range(3)]

    """
    file_path = Path(path)
    if file_path.exists():
        if file_path.suffix == ".csv":
            return _read_lazy_CSV(file_path)
        elif file_path.suffix == ".geojson":
            return _read_lazy_sectors_geojson(file_path)
        else:
            return iter(())
    else:
        return iter(())


def read_custom_sectors(path):
    """
    Reads airspace sectors from the given string path, supports csv and
    geo json.

    Returns a generator if the path exists or an empty generator if the path
    is not found or the file extension is unknown.

    The first row is the header row.

    Parameters
    ----------
    path The string path to the sector file, either csv or geojson.

    If the path is not a valid file we return an empty itereator.

    Examples:

    geojson :
    json_loc = "/Users/user/Downloads/ES_428.geojson"
    sectors_j = read_sectors(json_loc)
    next(sectors_j)
    [next(sectors_j) for _ in range(3)]

    csv:
    csv_loc = "/Users/user/Public/elementary_sectors.csv"
    sectors_c = read_sectors(csv_loc)
    next(sectors_c)
    [next(sectors_c) for _ in range(3)]

    """
    file_path = Path(path)
    if file_path.exists():
        if file_path.suffix == ".csv":
            return _read_lazy_CSV(file_path)
        elif file_path.suffix == ".geojson":
            return _read_lazy_custom_sectors_geojson(file_path)
        else:
            return iter(())
    else:
        return iter(())


def read_fleet_records(path):
    """
    Reads a fleet data file from the given string path, supports csv only.

    Returns a generator if the path exists or an empty generator if the path
    is not found or the file extension is unknown.

    The first row is the header row.

    Parameters
    ----------
    path The string path to the fleet csv file.

    If the path is not a valid file we return an empty itereator.

    Example:

    csv_loc = "/Users/user/Public/fleet_data-2017_07_01.csv"
    fleet_data = read_fleet_records(csv_loc)
    next(fleet_data)
    [next(fleet_data) for _ in range(3)]

    """
    file_path = Path(path)
    if file_path.exists():
        if file_path.suffix == ".csv":
            return _read_lazy_CSV(file_path)
        else:
            return iter(())
    else:
        return iter(())


def read_airports_records(path):
    """
    Reads an airport data file from the given string path, supports csv only.

    Returns a generator if the path exists or an empty generator if the path
    is not found or the file extension is unknown.

    The first row is the header row.

    Parameters
    ----------
    path The string path to the airports csv file.

    If the path is not a valid file we return an empty itereator.

    Example:

    csv_loc = "/Users/user/Public/airports-2017_07_01.csv"
    airports = read_airports_records(csv_loc)
    next(airports)
    [next(airports) for _ in range(3)]

    """
    file_path = Path(path)
    if file_path.exists():
        if file_path.suffix == ".csv":
            return _read_lazy_CSV(file_path)
        else:
            return iter(())
    else:
        return iter(())
