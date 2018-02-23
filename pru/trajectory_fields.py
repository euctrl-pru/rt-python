# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Fields of Eurocontrol PRU refined trajectory data and associated functions.
See: Eurocontrol PRU Trajectories Production Data Merging Report, section 2.
"""

from enum import IntEnum, unique
from datetime import datetime

FLIGHT_FIELDS = "FLIGHT_ID,CALLSIGN,AIRCRAFT_REG,AIRCRAFT_TYPE,AIRCRAFT_ADDRESS," \
    "ADEP,ADES,SSR_CODES,PERIOD_START,PERIOD_FINISH,SOURCE_IDS\n"
""" The fields of a flight record. """

POSITION_FIELDS = "FLIGHT_ID,DISTANCE,TIME_SOURCE,TIME_CALCULATED,LAT,LON,ALT," \
    "SPEED_GND,TRACK_GND,VERT_SPEED,ON_GROUND," \
    "SURVEILLANCE_SOURCE,AIRCRAFT_ADDRESS,SSR_CODE\n"
""" The fields of a positions record. """

FLIGHT_EVENT_FIELDS = "FLIGHT_ID,EVENT_TYPE,TIME_SOURCE,TIME_CALCULATED\n"
""" The fields of a flight event record. """

NEW_ID_FIELDS = 'FLIGHT_ID,NEW_FLIGHT_ID\n'
""" The fields of a new flight ids record. """

CSV_FILE_EXTENSION = '.csv'
""" The file extension of a comma separated variables (csv) file. """

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


def dms2decimal(degrees, minutes, seconds, negative=False):
    """
    Convert degrees, minutes, seconds (and optional sign) to a decimal angle.
    """
    angle = degrees + (minutes / 60.0) + (seconds / 3600.0)
    return -angle if (negative) else angle


def iso8601_date_parser(d):
    """ Parse an ISO 8601 date into python datetime format. """
    return datetime.strptime(d, ISO8601_DATE_FORMAT)


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


def read_iso8601_date_string(filename):
    """ Reads a date string in ISO 8601 format from the end of a csv file. """
    bz2_offset = len(BZ2_FILE_EXTENSION) if has_bz2_extension(filename) else 0
    date_end = -(len(CSV_FILE_EXTENSION) + bz2_offset)
    date_start = date_end - ISO8601_DATE_LENGTH
    return filename[date_start: date_end]


def create_iso8601_csv_filename(name, date, *, is_bz2=False):
    """ Create a filename string in ISO 8601 format. """
    filename = ''.join([name, date, CSV_FILE_EXTENSION])
    if is_bz2:
        filename += BZ2_FILE_EXTENSION
    return filename
