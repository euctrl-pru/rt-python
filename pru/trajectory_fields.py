# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Fields of Eurocontrol PRU refined trajectory data and associated functions.
See: Eurocontrol PRU Trajectories Production Data Merging Report, section 2.
"""

from enum import IntEnum, unique
from datetime import datetime, timedelta

FLIGHT_FIELDS = "FLIGHT_ID,CALLSIGN,AIRCRAFT_REG,AIRCRAFT_TYPE,AIRCRAFT_ADDRESS," \
    "ADEP,ADES,SSR_CODES,PERIOD_START,PERIOD_FINISH,SOURCE_IDS\n"
""" The fields of a flight record. """

POSITION_FIELDS = "FLIGHT_ID,DISTANCE,TIME,LAT,LON,ALT," \
    "SPEED_GND,TRACK_GND,VERT_SPEED,ON_GROUND," \
    "SURVEILLANCE_SOURCE,AIRCRAFT_ADDRESS,SSR_CODE\n"
""" The fields of a positions record. """

FLIGHT_EVENT_FIELDS = "FLIGHT_ID,EVENT_TYPE,TIME\n"
""" The fields of a flight event record. """

POSITION_ERROR_FIELDS = 'FLIGHT_ID,TOTAL,DUPLICATES,ADDRESSES,DISTANCE,ALTITUDE\n'
""" The fields of a positions error record. """

POSITION_METRICS_FIELDS = "FLIGHT_ID,PROFILE_TYPE,AV_PERIOD,IS_UNORDERED," \
    "TIME_SD,TIME_MAX,XT_SD,XT_MAX,ALT_SD,ALT_MAX\n"
""" The fields of a positions metrics record. """

NEW_ID_FIELDS = 'FLIGHT_ID,NEW_FLIGHT_ID\n'
""" The fields of a new flight ids record. """

AIRSPACE_INTERSECTION_FIELDS = 'FLIGHT_ID,SECTOR_ID,IS_EXIT,LAT,LON,ALT,TIME\n'
""" The fields of an airspace intersections record. """

AIRPORT_INTERSECTION_FIELDS = 'FLIGHT_ID,AIRPORT_ID,RADIUS,IS_DESTINATION,LAT,LON,ALT,TIME\n'
""" The fields of an airspace intersections record. """

CSV_FILE_EXTENSION = '.csv'
""" The file extension of a comma separated variables (csv) file. """

JSON_FILE_EXTENSION = '.json'
""" The file extension of a JavaScript Object Notation (json) file. """

BZ2_FILE_EXTENSION = '.bz2'
""" The file extension of a bz2 compressed file. """


@unique
class FlightEventType(IntEnum):
    """The types of flight event."""
    SCHEDULED_OFF_BLOCK = 0
    GATE_OUT = 1
    WHEELS_OFF = 2
    WHEELS_ON = 3
    GATE_IN = 4
    SCHEDULED_IN_BLOCK = 5


ISO8601_DATE_LENGTH = 10
""" The length of an ISO 8601 format date string"""

ISO8601_DATE_FORMAT = '%Y-%m-%d'
""" The ISO 8601 format of a date string. """

ISO8601_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
""" The ISO 8601 format of a date time string. """

ISO8601_DATETIME_US_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
""" The ISO 8601 format of a date time string in micoseconds. """


def dms2decimal(degrees, minutes, seconds, negative=False):
    """
    Convert degrees, minutes, seconds (and optional sign) to a decimal angle.
    """
    angle = degrees + (minutes / 60.0) + (seconds / 3600.0)
    return -angle if (negative) else angle


def iso8601_date_parser(d):
    """ Parse an ISO 8601 date into python datetime format. """
    return datetime.strptime(d, ISO8601_DATE_FORMAT)


def iso8601_previous_day(datestring):
    """ Return the date string of the previous day of a ISO 8601 date string. """
    date = iso8601_date_parser(datestring)
    prev_date = date - timedelta(1)
    return prev_date.strftime(ISO8601_DATE_FORMAT)


def compact_date(date):
    """
    Converts an ISO 8601 format date string into a compact date.

    Parameters
    ----------
    Date: a string date in iso format.

    Returns
    ----------
    A string date without hyphens.

    """
    return date.replace('-', '')


def split_dual_date(file_name):
    """
      Given a file name like A_2017-08-01_2017-09-01.csv.bz2
      or B_2017-08-01_2017-09-01.csv returns the from and until dates
      as a tuple
    """
    return (file_name.split("_")[-2], [sym.split(".") for sym in file_name.split("_")][-1][0])


def is_valid_iso8601_date(d):
    """ Determine whether a string is a valid ISO 8601 date. """
    try:
        iso8601_date_parser(d)
        return True
    except ValueError:
        return False


def iso8601_datetime_parser(d):
    """ Parse an ISO 8601 date and time into python datetime format. """
    return datetime.strptime(d, ISO8601_DATETIME_FORMAT)


def has_bz2_extension(filename):
    """ Determine whether a file has a .bz2 extension. """
    return filename[-len(BZ2_FILE_EXTENSION):] == BZ2_FILE_EXTENSION


def read_iso8601_date_string(filename, *, is_json=False):
    """ Reads a date string in ISO 8601 format from the end of a csv or json file. """
    bz2_offset = len(BZ2_FILE_EXTENSION) if has_bz2_extension(filename) else 0
    extension_offset = len(JSON_FILE_EXTENSION) if is_json \
        else len(CSV_FILE_EXTENSION)
    date_end = -(extension_offset + bz2_offset)
    date_start = date_end - ISO8601_DATE_LENGTH
    return filename[date_start: date_end]


def create_iso8601_csv_filename(name, date, *, is_bz2=False):
    """ Create a filename string in ISO 8601 format. """
    filename = ''.join([name, date, CSV_FILE_EXTENSION])
    if is_bz2:
        filename += BZ2_FILE_EXTENSION
    return filename
