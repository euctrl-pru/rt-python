#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Extract aircraft logger data from the files supplied by the PRU.
"""
import sys
import csv
import errno
import datetime
from enum import IntEnum, unique
from pru.trajectory_fields import POSITION_FIELDS, ISO8601_DATE_FORMAT
from pru.trajectory_files import create_positions_filename


@unique
class LogField(IntEnum):
    """The fields of an aircraft log file line."""
    AC_REG = 0
    FLIGHT_NUM = 1
    ALT = 2
    LAT = 3
    LONG = 4
    DATE = 5
    TIME = 6
    TAS = 7
    CAS = 8
    SPEED = 9
    MACH = 10


def excel_date_parser(d):
    """ Parse an excel date into python datetime format. """
    EXCEL_DATE_FORMAT = '%d/%m/%Y'
    return datetime.datetime.strptime(d, EXCEL_DATE_FORMAT)


def excel_time_parser(t):
    """ Parse an excel time into python datetime format. """
    EXCEL_TIME_FORMAT = '%H:%M:%S'
    return datetime.datetime.strptime(t, EXCEL_TIME_FORMAT)


class LoggerPosition:
    'A class for reading, storing and outputting a postion from a logger file line'

    def __init__(self, fields, date_time):
        self.id = fields[LogField.AC_REG]
        self.date_time = date_time
        self.latitude = float(fields[LogField.LAT])
        self.longitude = float(fields[LogField.LONG])
        self.altitude = int(fields[LogField.ALT])
        self.ground_speed = float(fields[LogField.SPEED])

    def __repr__(self):
        """ Print a row in POSITION_FIELDS format. """
        return '{},,{}Z,{:.5f},{:.5f},{:d},{:.1f}'. \
            format(self.id, self.date_time.isoformat(), self.latitude,
                   self.longitude, self.altitude, self.ground_speed)


class LoggerFlight:
    'A class for reading, storing and outputting data for a logger file flight'

    def __init__(self):
        self.id = ''
        self.callsign = ''
        self.time_str = ''
        self.positions = []

    def append(self, fields, time_offset=1):
        """ Append a line data if it contains date, lat, lon, etc and time is known.  """
        self.id = fields[LogField.AC_REG]

        # Get the callsign from FLIGHT_NUM field, if NOT zero
        if len(fields[LogField.FLIGHT_NUM]) > 1 and not self.callsign:
            self.callsign = fields[LogField.FLIGHT_NUM]

        # time_str is set when a TIME field is found and
        # cleared when a DATE field is found
        if fields[LogField.TIME]:
            self.time_str = fields[LogField.TIME]

        # if the tiem is know when a date is found, use it
        if self.time_str and fields[LogField.DATE]:
            time = excel_time_parser(self.time_str)
            date = excel_date_parser(fields[LogField.DATE])
            date_time = datetime.datetime.combine(date, time.time())

            # offset date_time by time_offset seconds
            date_time += time_offset * datetime.timedelta(seconds=1)
            self.positions.append(LoggerPosition(fields, date_time))

            # clear the time field for the next line
            self.time_str = ''


def convert_aircraft_logger_data(filename):

    flight = LoggerFlight()
    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader, None)  # skip the headers
            next(reader, None)
            next(reader, None)
            next(reader, None)
            next(reader, None)
            for row in reader:
                flight.append(row)

        print('File:', filename, 'read ok')

    except EnvironmentError:
        print('could not read file: %s', filename)
        return errno.ENOENT

    date_time = flight.positions[0].date_time
    date_time_str = date_time.strftime(ISO8601_DATE_FORMAT)
    positions_file = create_positions_filename(flight.callsign, date_time_str)
    try:
        with open(positions_file, 'w') as file:
            file.write(POSITION_FIELDS)
            for pos in flight.positions:
                print(pos, file=file)

        print('written file:', positions_file)

    except EnvironmentError:
        print('could not write file:', positions_file)
        return errno.EACCES

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: convert_aircraft_logger_data.py <logger_filename.csv>')
        sys.exit(errno.EINVAL)

    error_code = convert_aircraft_logger_data(sys.argv[1])
    if error_code:
        sys.exit(error_code)
