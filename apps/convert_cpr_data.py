#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
# Software to read a Eurocontrol archieved Correlated Position Report (CPR) file.

import sys
import os
import gzip
import csv
import pandas as pd
from enum import IntEnum, unique
import datetime
from pru.trajectory_fields import \
    FLIGHT_FIELDS, FLIGHT_EVENT_FIELDS, POSITION_FIELDS, dms2decimal, \
    FlightEventType, ISO8601_DATE_FORMAT, create_iso8601_csv_filename
from pru.logger import logger


@unique
class CprField(IntEnum):
    """The fields of an archived Correlated Position Report (CPR) line."""
    LINE_NUMBER = 0
    TACT_ID = 1
    ETFMS_RECEIPT = 2
    DATE_TIME = 3
    BLOCK_NUMBER = 4
    RECORD_NUMBER = 5
    SAC = 6
    SIC = 7
    CALLSIGN = 8
    DEPARTURE = 9
    DESTINATION = 10
    EOBT = 11
    LAT_LONG = 12
    FLIGHT_LEVEL = 13
    TRACK_SERVICE = 14
    SSR_CODE = 15
    TRACK_VELOCITY = 16
    TRACK_MAGNETIC = 17
    VERTICAL_RATE = 18
    VERTICAL_MODE = 19
    IFPS_ID = 20
    AIRCRAFT_ADDRESS = 21


MAX_SSR_CODES = 10
""" The maximum number of SSR codes to output per flight. """

CPR_DATE_FORMAT = '%Y%m%d'
""" The format of a date string in a CPR filename. """

CPR_DATETIME_FORMAT = '%y/%m/%d %H:%M:%S'
""" The format of a date time string in a CPR file. """


def cpr_date_parser(d):
    """ Parse a CPR date into python datetime format. """
    return datetime.datetime.strptime(d, CPR_DATE_FORMAT)


def cpr_datetime_parser(d):
    """ Parse a CPR date and time into python datetime format. """
    return datetime.datetime.strptime(d, CPR_DATETIME_FORMAT)


def cpr_latlong2decimal(input):
    """
    Convert a CPR file Latitude and Longitude into decimal angles.
    """
    latitude = -90.0
    longitude = -180.0

    if (16 == len(input)):
        lat_degrees = int(input[0:2])
        lat_minutes = int(input[2:4])
        lat_seconds = int(input[4:6])
        lat_negative = ('S' == input[6])

        lng_degrees = int(input[8:11])
        lng_minutes = int(input[11:13])
        lng_seconds = int(input[13:15])
        lng_negative = ('W' == input[15])

        latitude = dms2decimal(lat_degrees, lat_minutes, lat_seconds, lat_negative)
        longitude = dms2decimal(lng_degrees, lng_minutes, lng_seconds, lng_negative)

    return latitude, longitude


def cpr_track2decimal(input):
    """
    Convert a CPR file track into a decimal angle.
    """
    degrees = int(input[0:3])
    minutes = int(input[4:6])
    seconds = int(input[7:9])

    return dms2decimal(degrees, minutes, seconds)


class CprPosition:
    'A class for reading, storing and outputting a postion from a CPR file line entry'

    def __init__(self, cpr_fields):
        self.id = int(cpr_fields[CprField.TACT_ID]) if cpr_fields[CprField.TACT_ID] else 0
        self.date_time = cpr_datetime_parser(cpr_fields[CprField.DATE_TIME])
        self.sac = int(cpr_fields[CprField.SAC]) if cpr_fields[CprField.SAC] else 0
        self.sic = int(cpr_fields[CprField.SIC]) if cpr_fields[CprField.SIC] else 0

        self.latitude, self.longitude = \
            cpr_latlong2decimal(cpr_fields[CprField.LAT_LONG])

        self.altitude = 0
        if cpr_fields[CprField.FLIGHT_LEVEL]:
            self.altitude = 100 * int(cpr_fields[CprField.FLIGHT_LEVEL])
        self.ssr_code = cpr_fields[CprField.SSR_CODE]
        self.ground_speed = 0.0
        if cpr_fields[CprField.TRACK_VELOCITY]:
            self.ground_speed = float(cpr_fields[CprField.TRACK_VELOCITY])
        self.track_magnetic = -1.0
        if cpr_fields[CprField.TRACK_MAGNETIC]:
            self.track_magnetic = cpr_track2decimal(cpr_fields[CprField.TRACK_MAGNETIC])
        self.vertical_rate = 0
        if cpr_fields[CprField.VERTICAL_RATE]:
            self.vertical_rate = int(cpr_fields[CprField.VERTICAL_RATE])
        self.aircraft_address = ''
        if cpr_fields[CprField.AIRCRAFT_ADDRESS]:
            self.aircraft_address = '0x' + cpr_fields[CprField.AIRCRAFT_ADDRESS]

    def __hash__(self):
        return hash(hash(self.id) ^ hash(self.date_time) ^
                    hash(self.latitude) ^ hash(self.longitude) ^
                    hash(self.altitude) ^ hash(self.ssr_code) ^
                    hash(self.sac) ^ hash(self.sic) ^
                    hash(self.aircraft_address))

    def __eq__(self, other):
        return (self.id == other.id) \
            and (self.date_time == other.date_time) \
            and (self.latitude == other.latitude) \
            and (self.longitude == other.longitude) \
            and (self.altitude == other.altitude) \
            and (self.ssr_code == other.ssr_code) \
            and (self.sac == other.sac) \
            and (self.sic == other.sic) \
            and (self.aircraft_address == other.aircraft_address)

    def __repr__(self):
        return '{:d},,{}Z,,{:.5f},{:.5f},{:d},{:.1f},{:.5f},{:d},,CPR 0x{:02x} 0x{:02x},{},\'{}\''. \
            format(self.id, self.date_time.isoformat(), self.latitude, self.longitude,
                   self.altitude, self.ground_speed, self.track_magnetic, self.vertical_rate,
                   self.sac, self.sic, self.aircraft_address, self.ssr_code)


class CprFlight:
    'A class for reading, storing and outputting data for a CPR flight'

    def __init__(self, cpr_fields):
        self.id = int(cpr_fields[CprField.TACT_ID]) if cpr_fields[CprField.TACT_ID] else 0
        self.callsign = cpr_fields[CprField.CALLSIGN]
        self.departure = cpr_fields[CprField.DEPARTURE]
        self.destination = cpr_fields[CprField.DESTINATION]
        self.eobt = cpr_datetime_parser(cpr_fields[CprField.EOBT]) \
            if (0 < len(cpr_fields[CprField.EOBT])) else ''
        self.aircraft_address = ''
        self.callsign2 = ''
        self.aircraft_address2 = ''
        self.aircraft_addresses = []
        self.ssr_codes = []
        self.positions = []

    def append(self, cpr_fields):
        self.positions.append(CprPosition(cpr_fields))
        if not self.callsign:
            self.callsign = cpr_fields[CprField.CALLSIGN]
        elif self.callsign != cpr_fields[CprField.CALLSIGN]:
            self.callsign2 = cpr_fields[CprField.CALLSIGN]

        if cpr_fields[CprField.AIRCRAFT_ADDRESS]:
            mode_s_address = '0x' + cpr_fields[CprField.AIRCRAFT_ADDRESS]
            self.aircraft_addresses.append(mode_s_address)

        ssr_code = cpr_fields[CprField.SSR_CODE]
        if ssr_code and (ssr_code != '0000') and (ssr_code not in self.ssr_codes):
            self.ssr_codes.append(ssr_code)

    def sort(self):
        # Convert to a set and back to remove duplicate positions
        self.positions = list(set(self.positions))
        self.positions.sort(key=lambda position: position.date_time)

        aircraft_addresses = pd.Series(self.aircraft_addresses)
        addresses = aircraft_addresses.value_counts().index.tolist()
        if addresses:
            self.aircraft_address = addresses[0]
            if len(addresses) > 1:
                self.aircraft_address2 = addresses[1]

        # Ignore 0000 squawks
        if self.ssr_codes and ('0000' in self.ssr_codes):
            self.ssr_codes.remove('0000')

        if len(self.ssr_codes) > MAX_SSR_CODES:
            self.ssr_codes = self.ssr_codes[: MAX_SSR_CODES]

    def is_valid(self):
        """ Determine whether flight is valid """
        return self.id and (len(self.positions) > 1)

    def __repr__(self):
        ssr_code_str = ''
        if self.ssr_codes:
            for ssr_code in self.ssr_codes:
                ssr_code_str += ssr_code + ' '

            ssr_code_str = ssr_code_str[: -1]

        return '{:d},{},,,{},{},{},\'{}\',{}Z,{}Z,{}'. \
            format(self.id, self.callsign, self.aircraft_address,
                   self.departure, self.destination, ssr_code_str,
                   self.positions[0].date_time.isoformat(),
                   self.positions[-1].date_time.isoformat(),
                   self.aircraft_address2)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: convert_cpr_data.py <filename>')
        sys.exit(2)

    log = logger(os.path.basename(sys.argv[0]))

    filename = sys.argv[1]

    # Extract the date string from the filename and validate it
    file_date = os.path.basename(filename)[2:10]
    date = datetime.time()
    try:
        date = cpr_date_parser(file_date)
    except ValueError:
        log.error('cpr positions file: %s, invalid date: %s',
                  filename, file_date)
        sys.exit(2)

    # Convert the file date string into ISO 8601 format
    file_date = date.strftime(ISO8601_DATE_FORMAT)

    log.info('cpr file: %s', filename)

    # A dict to hold the CPR flights
    flights = {}

    # Read the CPR file into flights
    try:
        is_gzip = (filename[-1] == 'z')
        with gzip.open(filename, 'rt',  newline="") if (is_gzip) else \
                open(filename, 'r') as file:
            reader = csv.reader(file, delimiter=';')
            for row in reader:
                flights.setdefault(row[CprField.TACT_ID],
                                   CprFlight(row)).append(row)

    except EnvironmentError:
        log.error('could not read file: %s', filename)
        sys.exit(2)

    # sort positions in date time (time of track) order
    for key, values in flights.items():
        values.sort()
    log.info('cpr file read ok')

    valid_flights = 0

    # Output the CPR flight data for all valid flights
    flight_file = create_iso8601_csv_filename('cpr_flights_', file_date)
    try:
        with open(flight_file, 'w') as file:
            file.write(FLIGHT_FIELDS)
            for key, value in sorted(flights.items()):
                if value.is_valid:
                    print(value, file=file)
                    valid_flights += 1

    except EnvironmentError:
        log.error('could not write file: %s', flight_file)

    log.info('written file: %s', flight_file)

    # Output the CPR event data for all valid flights
    events_file = create_iso8601_csv_filename('cpr_events_', file_date)
    try:
        with open(events_file, 'w') as file:
            file.write(FLIGHT_EVENT_FIELDS)
            for key, value in sorted(flights.items()):
                # Note: an event requires an eobt as well as a valid flight
                if value.is_valid and value.eobt:
                    scheduled_time = value.eobt.isoformat() + 'Z'
                    print(key, int(FlightEventType.SCHEDULED_OFF_BLOCK),
                          scheduled_time, sep=',', file=file)

    except EnvironmentError:
        log.error('could not write file: %s', events_file)

    log.info('written file: %s', events_file)

    # Output the CPR position data for all flights
    positions_file = create_iso8601_csv_filename('cpr_positions_', file_date)
    try:
        with open(positions_file, 'w') as file:
            file.write(POSITION_FIELDS)
            for key, value in sorted(flights.items()):
                if value.is_valid:
                    for pos in value.positions:
                        print(pos, file=file)

    except EnvironmentError:
        log.error('could not write file: %s', positions_file)

    log.info('written file: %s', positions_file)

    log.info('cpr conversion complete for %s flights on %s',
             valid_flights, file_date)
