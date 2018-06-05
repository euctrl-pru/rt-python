#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Software to read Eurocontrol ADS-B flights and points files.
"""

import sys
import os
import bz2
import csv
import errno
from enum import IntEnum, unique
from pru.trajectory_fields import \
    FLIGHT_FIELDS, POSITION_FIELDS, is_valid_iso8601_date, iso8601_datetime_parser, \
    has_bz2_extension, read_iso8601_date_string
from pru.trajectory_files import create_convert_fr24_filenames
from pru.logger import logger

log = logger(__name__)


@unique
class AdsbFlightField(IntEnum):
    'The fields of an ADS-B flights line.'
    FLIGHT_ID = 0
    START_TIME = 1
    ADEP = 2
    ADES = 3
    CALLSIGN = 4
    FLIGHT = 5
    REG = 6
    MODEL = 7
    ADDRESS = 8


@unique
class AdsbPointField(IntEnum):
    'The fields of an ADS-B points line.'
    FLIGHT_ID = 0
    LAT = 1
    LONG = 2
    TRACK_GND = 3
    ALT = 4
    SPEED = 5
    SQUAWK = 6
    RADAR_ID = 7
    EVENT_TIME = 8
    ON_GROUND = 9
    VERT_SPEED = 10


ICAO_SPECIAL_AIRCRAFT_TYPE_DESIGNATORS = frozenset(['0000',
                                                    'BALL', 'GLID', 'GRND', 'GYRO',
                                                    'PARA', 'UHEL', 'ULAC', 'SHIP'])
"""
ICAO codes of special aircraft and others i.e.: 0000 and GRND.
Not required in the output.
"""


class AdsbPosition:
    'A class for reading, storing and outputting a postion from an ADS-B file line entry'

    def __init__(self, adsb_fields, aircraft_address):
        self.id = '0x' + adsb_fields[AdsbPointField.FLIGHT_ID]
        self.date_time = iso8601_datetime_parser(adsb_fields[AdsbPointField.EVENT_TIME])
        self.radar_id = adsb_fields[AdsbPointField.RADAR_ID]
        self.latitude = float(adsb_fields[AdsbPointField.LAT])
        self.longitude = float(adsb_fields[AdsbPointField.LONG])
        self.altitude = int(adsb_fields[AdsbPointField.ALT])
        self.ssr_code = adsb_fields[AdsbPointField.SQUAWK]

        self.ground_speed = 0.0
        if adsb_fields[AdsbPointField.SPEED]:
            self.ground_speed = float(adsb_fields[AdsbPointField.SPEED])
        self.ground_track = -1.0
        if adsb_fields[AdsbPointField.TRACK_GND]:
            self.ground_track = float(adsb_fields[AdsbPointField.TRACK_GND])
        self.vertical_rate = 0
        if adsb_fields[AdsbPointField.VERT_SPEED]:
            self.vertical_rate = int(adsb_fields[AdsbPointField.VERT_SPEED])

        self.on_ground = adsb_fields[AdsbPointField.ON_GROUND]
        self.aircraft_address = aircraft_address

    def __hash__(self):
        return hash(hash(self.id) ^ hash(self.date_time) ^
                    hash(self.latitude) ^ hash(self.longitude) ^
                    hash(self.altitude) ^ hash(self.ssr_code) ^
                    hash(self.radar_id) ^ hash(self.aircraft_address))

    def __eq__(self, other):
        return (self.id == other.id) \
            and (self.date_time == other.date_time) \
            and (self.latitude == other.latitude) \
            and (self.longitude == other.longitude) \
            and (self.altitude == other.altitude) \
            and (self.ssr_code == other.ssr_code) \
            and (self.radar_id == other.radar_id) \
            and (self.aircraft_address == other.aircraft_address)

    def __repr__(self):
        return '{},,{}Z,{:.5f},{:.5f},{:d},{:.1f},{:.3f},{:d},{},FR24 {},{},\'{}\''. \
            format(self.id, self.date_time.isoformat(), self.latitude, self.longitude, self.altitude,
                   self.ground_speed, self.ground_track, self.vertical_rate,
                   self.on_ground, self.radar_id, self.aircraft_address, self.ssr_code)


class AdsbFlight:
    'A class for reading, storing and outputting data for an ADS-B flight'

    def __init__(self, adsb_fields):
        self.id = '0x' + adsb_fields[AdsbFlightField.FLIGHT_ID]
        self.callsign = adsb_fields[AdsbFlightField.CALLSIGN]
        self.registration = adsb_fields[AdsbFlightField.REG]
        self.aircraft_type = adsb_fields[AdsbFlightField.MODEL]
        self.departure = adsb_fields[AdsbFlightField.ADEP]
        self.destination = adsb_fields[AdsbFlightField.ADES]
        self.aircraft_address = '0x' + adsb_fields[AdsbFlightField.ADDRESS]
        self.ssr_codes = []
        self.positions = []
        is_special_aircraft_type = self.aircraft_type and \
            (self.aircraft_type in ICAO_SPECIAL_AIRCRAFT_TYPE_DESIGNATORS)
        is_invalid_aircraft_address = (self.aircraft_address == '0x000000') or \
            (self.aircraft_address == '0xFFFFFF')
        self.is_valid = not is_special_aircraft_type and \
            not is_invalid_aircraft_address

    def append(self, adsb_fields):
        self.positions.append(AdsbPosition(adsb_fields, self.aircraft_address))

        ssr_code = adsb_fields[AdsbPointField.SQUAWK]
        if ssr_code and (ssr_code != '0000') and (ssr_code not in self.ssr_codes):
            self.ssr_codes.append(ssr_code)

    def sort(self):
        # Convert to a set and back to remove duplicate positions
        self.positions = list(set(self.positions))

        self.is_valid = self.is_valid and (len(self.positions) > 1)
        if self.is_valid:
            self.positions.sort(key=lambda position: position.date_time)

            # Ignore 0000 squawks
            if self.ssr_codes and ('0000' in self.ssr_codes):
                self.ssr_codes.remove('0000')

    def __repr__(self):
        ssr_code_str = ''
        if self.ssr_codes:
            ssr_code_str = ' '.join(self.ssr_codes)

        return '{},{},{},{},{},{},{},[{}],{}Z,{}Z,[]'. \
            format(self.id, self.callsign, self.registration, self.aircraft_type,
                   self.aircraft_address,
                   self.departure, self.destination, ssr_code_str,
                   self.positions[0].date_time.isoformat(),
                   self.positions[-1].date_time.isoformat())


def convert_fr24_data(filenames):

    flights_filename = filenames[0]
    points_filename = filenames[1]

    if flights_filename == points_filename:
        log.error('Files are the same! Flights filename: %s, points filename: %s',
                  flights_filename, points_filename)
        return errno.EINVAL

    # Extract the date string from the filename and validate it
    flights_date = read_iso8601_date_string(flights_filename)
    if is_valid_iso8601_date(flights_date):
        log.info('fr24 flights file: %s', flights_filename)
    else:
        log.error('fr24 flights file: %s, invalid date: %s',
                  flights_filename, flights_date)
        return errno.EINVAL

    # Extract the date string from the filename and validate it
    points_date = read_iso8601_date_string(points_filename)
    if is_valid_iso8601_date(points_date):
        log.info('fr24 points file: %s', points_filename)
    else:
        log.error('fr24 points file: %s, invalid date: %s',
                  points_filename, points_date)
        return errno.EINVAL

    if flights_date != points_date:
        log.error('Files are not for the same date! Flights date: %s, points date: %s',
                  flights_date, points_date)
        return errno.EINVAL

    # A dict to hold the ADS-B flights
    flights = {}

    # Read the ADS-B flights file into flights
    try:
        is_bz2 = has_bz2_extension(flights_filename)
        with bz2.open(flights_filename, 'rt',  newline="") if (is_bz2) else \
                open(flights_filename, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            next(reader, None)  # skip the headers
            for row in reader:
                flights.setdefault(row[AdsbFlightField.FLIGHT_ID],
                                   AdsbFlight(row))

    except EnvironmentError:
        log.error('could not read file: %s', flights_filename)
        return errno.ENOENT

    log.info('fr24 flights read ok')

    # Read the ADS-B points file into flights
    try:
        is_bz2 = has_bz2_extension(points_filename)
        with bz2.open(points_filename, 'rt',  newline="") if (is_bz2) else \
                open(points_filename, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            next(reader, None)  # skip the headers
            for row in reader:
                if row[AdsbPointField.FLIGHT_ID] in flights:
                    flights[row[AdsbPointField.FLIGHT_ID]].append(row)

    except EnvironmentError:
        log.error('could not read file: %s', points_filename)
        return errno.ENOENT

    log.info('fr24 points read ok')

    # sort positions in date time (of position) order
    for key, values in flights.items():
        values.sort()
    log.info('fr24 points sorted')

    valid_flights = 0

    # Output the ADS-B flight data for all flights
    output_files = create_convert_fr24_filenames(flights_date)
    flight_file = output_files[0]
    try:
        with open(flight_file, 'w') as file:
            file.write(FLIGHT_FIELDS)
            for key, values in sorted(flights.items()):
                if values.is_valid:
                    print(values, file=file)
                    valid_flights += 1

        log.info('written file: %s', flight_file)

    except EnvironmentError:
        log.error('could not write file: %s', flight_file)

    # Output the ADS-B position data for all flights
    positions_file = output_files[1]
    try:
        with open(positions_file, 'w') as file:
            file.write(POSITION_FIELDS)
            for key, values in sorted(flights.items()):
                if values.is_valid:
                    for pos in values.positions:
                        print(pos, file=file)

        log.info('written file: %s', positions_file)

    except EnvironmentError:
        log.error('could not write file: %s', positions_file)
        return errno.EACCES

    log.info('fr24 conversion complete for %s flights on %s',
             valid_flights, points_date)

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: convert_fr24_data py <flights_filename> <points_filename>')
        sys.exit(errno.EINVAL)

    error_code = convert_fr24_data(sys.argv[1:])
    if error_code:
        sys.exit(error_code)
