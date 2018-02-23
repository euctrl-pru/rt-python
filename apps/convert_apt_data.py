#!/usr/bin/env python
#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Software to read Eurocontrol APDS files.
"""

import sys
import os
import bz2
import csv
import pandas as pd
from enum import IntEnum, unique
from pru.trajectory_fields import \
    FLIGHT_FIELDS, FLIGHT_EVENT_FIELDS, POSITION_FIELDS, FlightEventType, \
    iso8601_date_parser, iso8601_datetime_parser, has_bz2_extension, \
    read_iso8601_date_string, create_iso8601_csv_filename
from pru.logger import logger


@unique
class AptField(IntEnum):
    'The fields of an APT line.'
    APDS_ID = 0
    AP_C_FLTID = 1
    AP_C_REG = 2
    ADEP_ICAO = 3
    ADES_ICAO = 4
    SRC_PHASE = 5
    MVT_TIME_UTC = 6
    BLOCK_TIME_UTC = 7
    SCHED_TIME_UTC = 8
    ARCTYP = 9
    AP_C_RWY = 10
    AP_C_STND = 11
    C40_CROSS_TIME = 12
    C40_CROSS_LAT = 13
    C40_CROSS_LON = 14
    C40_CROSS_FL = 15
    C40_BEARING = 16
    C100_CROSS_TIME = 17
    C100_CROSS_LAT = 18
    C100_CROSS_LON = 19
    C100_CROSS_FL = 20
    C100_BEARING = 21


class AptEvent:
    'A class for storing and outputting a APT event'

    def __init__(self, id, event, date_time):
        self.id = id
        self.event = event
        self.date_time = date_time

    def __lt__(self, other):
        return self.event < other.event

    def __repr__(self):
        return '{},{},{}Z'. \
            format(self.id, self.event, self.date_time.isoformat())


class AptPosition:
    'A class for storing and outputting a APT poistion'

    def __init__(self, id, date_time, latitude, longitude, airport, stand):
        self.id = id
        self.date_time = date_time
        self.latitude = latitude
        self.longitude = longitude
        self.airport = airport
        self.stand = stand

    def __lt__(self, other):
        return self.date_time < other.date_time

    def __repr__(self):
        return '{},,{}Z,,{:.5f},{:.5f},,,,,1,APT {} {},,'. \
            format(self.id, self.date_time.isoformat(),
                   self.latitude, self.longitude, self.airport, self.stand)


class AptFlight:
    'A class for reading, storing and outputting data for an APT flight'

    def __init__(self, apt_fields, airport_stands):
        self.id = apt_fields[AptField.APDS_ID]
        self.callsign = apt_fields[AptField.AP_C_FLTID]
        self.registration = apt_fields[AptField.AP_C_REG]
        self.aircraft_type = apt_fields[AptField.ARCTYP]
        self.departure = apt_fields[AptField.ADEP_ICAO]
        self.destination = apt_fields[AptField.ADES_ICAO]
        self.events = []
        self.positions = []

        is_arrival = (apt_fields[AptField.SRC_PHASE] == 'ARR')
        airport = self.destination if (is_arrival) else self.destination

        # Get the take-off or landing event
        if apt_fields[AptField.MVT_TIME_UTC]:
            movement_event = FlightEventType.WHEELS_ON if (is_arrival) \
                else FlightEventType.WHEELS_OFF
            movement_time = iso8601_datetime_parser(apt_fields[AptField.MVT_TIME_UTC])
            self.events.append(AptEvent(self.id, movement_event, movement_time))

            # if the airport and runway is known, create a position
            # if airport and apt_fields[AptField.AP_C_RWY]:

        # Get the actual off-block or in-block event
        if apt_fields[AptField.BLOCK_TIME_UTC]:
            block_event = FlightEventType.GATE_IN if (is_arrival) \
                else FlightEventType.GATE_OUT
            block_time = iso8601_datetime_parser(apt_fields[AptField.BLOCK_TIME_UTC])
            self.events.append(AptEvent(self.id, block_event, block_time))

            # if the airport and stand is known, create a position
            if len(airport_stands):
                stand = apt_fields[AptField.AP_C_STND]
                if airport and stand:
                    if (airport, stand) in airport_stands.index:
                        pos = airport_stands.loc[airport, stand]
                        latitude = pos['LAT']
                        longitude = pos['LON']
                        self.positions.append(AptPosition(self.id, block_time,
                                                          latitude, longitude,
                                                          airport, stand))

        # Get the scheduled off-block or in-block event
        if apt_fields[AptField.SCHED_TIME_UTC]:
            scheduled_event = FlightEventType.SCHEDULED_IN_BLOCK if (is_arrival) \
                else FlightEventType.SCHEDULED_OFF_BLOCK
            scheduled_time = iso8601_datetime_parser(apt_fields[AptField.SCHED_TIME_UTC])
            self.events.append(AptEvent(self.id, scheduled_event, scheduled_time))

    def __repr__(self):
        return '{},{},{},{},,{},{}'. \
            format(self.id, self.callsign, self.registration, self.aircraft_type,
                   self.departure, self.destination)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: convert_apt_data py <apt_filename> [stands_filename]')
        sys.exit(2)

    log = logger(os.path.basename(sys.argv[0]))

    filename = sys.argv[1]

    # Get the stands_filename, if supplied
    stands_filename = ''
    if len(sys.argv) >= 3:
        stands_filename = sys.argv[2]

    # Extract the start date string from the filename and validate it
    start_date = os.path.basename(filename)[22:32]
    try:
        iso8601_date_parser(start_date)
    except ValueError:
        log.error('apt data file: %s, invalid start date: %s',
                  filename, start_date)
        sys.exit(2)

    # Extract the finish date string from the filename and validate it
    finish_date = read_iso8601_date_string(filename)
    try:
        iso8601_date_parser(finish_date)
    except ValueError:
        log.error('apt data file: %s, invalid finish date: %s',
                  filename, finish_date)
        sys.exit(2)

    log.info('apt data file: %s', filename)

    airport_stands_df = pd.DataFrame()
    if stands_filename:
        try:
            airport_stands_df = pd.read_csv(stands_filename,
                                            index_col=['ICAO_ID', 'STAND_ID'])
            airport_stands_df.sort_index()
        except EnvironmentError:
            log.error('could not read file: %s', stands_filename)
            sys.exit(2)

        log.info('apt stands file: %s', stands_filename)
    else:
        log.info('apt stands not provided')

    # A dict to hold the APT flights
    flights = {}

    # Read the APT flights file into flights
    try:
        is_bz2 = has_bz2_extension(filename)
        with bz2.open(filename, 'rt',  newline="") if (is_bz2) else \
                open(filename, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            next(reader, None)  # skip the headers
            for row in reader:
                flights.setdefault(row[AptField.APDS_ID],
                                   AptFlight(row, airport_stands_df))

    except EnvironmentError:
        log.error('could not read file: %s', filename)
        sys.exit(2)

    log.info('apt flights read ok')

    valid_flights = 0

    # Output the APT flight data
    # finish_date
    flight_file = create_iso8601_csv_filename('apt_flights_' + start_date + '_',
                                              finish_date)
    try:
        with open(flight_file, 'w') as file:
            file.write(FLIGHT_FIELDS)
            for key, value in sorted(flights.items()):
                print(value, file=file)
                valid_flights += 1

    except EnvironmentError:
        log.error('could not write file: %s', flight_file)

    log.info('written file: %s', flight_file)

    # Output the APT event data
    event_file = create_iso8601_csv_filename('apt_events_' + start_date + '_',
                                             finish_date)
    try:
        with open(event_file, 'w') as file:
            file.write(FLIGHT_EVENT_FIELDS)
            for key, value in sorted(flights.items()):
                for event in sorted(value.events):
                    print(event, file=file)

    except EnvironmentError:
        log.error('could not write file: %s', event_file)
        sys.exit(2)

    log.info('written file: %s', event_file)

    # if airport stand data was provided
    if len(airport_stands_df):
        # Output the APT position data
        positions_file = create_iso8601_csv_filename('apt_positions_' + start_date + '_',
                                                     finish_date)
        with open(positions_file, 'w') as file:
            file.write(POSITION_FIELDS)
            for key, value in sorted(flights.items()):
                for event in sorted(value.positions):
                    print(event, file=file)

        log.info('written file: %s', positions_file)

    log.info('apt conversion complete for %s flights on %s',
             valid_flights, start_date)
