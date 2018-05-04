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
import errno
import pandas as pd
from enum import IntEnum, unique
from pru.trajectory_fields import \
    FLIGHT_FIELDS, FLIGHT_EVENT_FIELDS, POSITION_FIELDS, FlightEventType, \
    is_valid_iso8601_date, iso8601_datetime_parser, has_bz2_extension, \
    split_dual_date
from pru.trajectory_files import create_convert_apds_filenames
from pru.logger import logger

log = logger(__name__)


@unique
class ApdsField(IntEnum):
    'The fields of an APDS line.'
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


class ApdsEvent:
    'A class for storing and outputting a APDS event'

    def __init__(self, id, event, date_time):
        self.id = id
        self.event = event
        self.date_time = date_time

    def __lt__(self, other):
        return self.event < other.event

    def __repr__(self):
        return '{},{},{}Z'. \
            format(self.id, self.event, self.date_time.isoformat())


class ApdsPosition:
    'A class for storing and outputting a APDS poistion'

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
        return '{},,{}Z,,{:.5f},{:.5f},,,,,1,APDS {} {},,'. \
            format(self.id, self.date_time.isoformat(),
                   self.latitude, self.longitude, self.airport, self.stand)


class ApdsFlight:
    'A class for reading, storing and outputting data for an APDS flight'

    def __init__(self, apds_fields, airport_stands):
        self.id = apds_fields[ApdsField.APDS_ID]
        self.callsign = apds_fields[ApdsField.AP_C_FLTID]
        self.registration = apds_fields[ApdsField.AP_C_REG]
        self.aircraft_type = apds_fields[ApdsField.ARCTYP]
        self.departure = apds_fields[ApdsField.ADEP_ICAO]
        self.destination = apds_fields[ApdsField.ADES_ICAO]
        self.events = []
        self.positions = []

        is_arrival = (apds_fields[ApdsField.SRC_PHASE] == 'ARR')
        airport = self.destination if (is_arrival) else self.destination

        # Get the take-off or landing event
        if apds_fields[ApdsField.MVT_TIME_UTC]:
            movement_event = FlightEventType.WHEELS_ON if (is_arrival) \
                else FlightEventType.WHEELS_OFF
            movement_time = iso8601_datetime_parser(apds_fields[ApdsField.MVT_TIME_UTC])
            self.events.append(ApdsEvent(self.id, movement_event, movement_time))

            # if the airport and runway is known, create a position
            # if airport and apds_fields[ApdsField.AP_C_RWY]:

        # Get the actual off-block or in-block event
        if apds_fields[ApdsField.BLOCK_TIME_UTC]:
            block_event = FlightEventType.GATE_IN if (is_arrival) \
                else FlightEventType.GATE_OUT
            block_time = iso8601_datetime_parser(apds_fields[ApdsField.BLOCK_TIME_UTC])
            self.events.append(ApdsEvent(self.id, block_event, block_time))

            # if the airport and stand is known, create a position
            if len(airport_stands):
                stand = apds_fields[ApdsField.AP_C_STND]
                if airport and stand:
                    if (airport, stand) in airport_stands.index:
                        pos = airport_stands.loc[airport, stand]
                        latitude = pos['LAT']
                        longitude = pos['LON']
                        self.positions.append(ApdsPosition(self.id, block_time,
                                                           latitude, longitude,
                                                           airport, stand))

        # Get the scheduled off-block or in-block event
        if apds_fields[ApdsField.SCHED_TIME_UTC]:
            scheduled_event = FlightEventType.SCHEDULED_IN_BLOCK if (is_arrival) \
                else FlightEventType.SCHEDULED_OFF_BLOCK
            scheduled_time = iso8601_datetime_parser(apds_fields[ApdsField.SCHED_TIME_UTC])
            self.events.append(ApdsEvent(self.id, scheduled_event, scheduled_time))

    def __repr__(self):
        return '{},{},{},{},,{},{}'. \
            format(self.id, self.callsign, self.registration, self.aircraft_type,
                   self.departure, self.destination)


def convert_apds_data(filename, stands_filename):

    # Extract the start and finish date strings from the filename
    start_date, finish_date = split_dual_date(os.path.basename(filename))
    if not is_valid_iso8601_date(start_date):
        log.error('apds data file: %s, invalid start date: %s',
                  filename, start_date)
        return errno.EINVAL

    # validate the finish date string from the filename
    if not is_valid_iso8601_date(finish_date):
        log.error('apds data file: %s, invalid finish date: %s',
                  filename, finish_date)
        return errno.EINVAL

    log.info('apds data file: %s', filename)

    airport_stands_df = pd.DataFrame()
    if stands_filename:
        try:
            airport_stands_df = pd.read_csv(stands_filename,
                                            index_col=['ICAO_ID', 'STAND_ID'],
                                            memory_map=True)
            airport_stands_df.sort_index()
        except EnvironmentError:
            log.error('could not read file: %s', stands_filename)
            return errno.ENOENT

        log.info('airport stands file: %s', stands_filename)
    else:
        log.info('airport stands not provided')

    # A dict to hold the APDS flights
    flights = {}

    # Read the APDS flights file into flights
    try:
        is_bz2 = has_bz2_extension(filename)
        with bz2.open(filename, 'rt',  newline="") if (is_bz2) else \
                open(filename, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            next(reader, None)  # skip the headers
            for row in reader:
                flights.setdefault(row[ApdsField.APDS_ID],
                                   ApdsFlight(row, airport_stands_df))

    except EnvironmentError:
        log.error('could not read file: %s', filename)
        return errno.ENOENT

    log.info('apds flights read ok')

    valid_flights = 0

    # Output the APDS flight data
    # finish_date
    output_files = create_convert_apds_filenames(start_date, finish_date)
    flight_file = output_files[0]
    try:
        with open(flight_file, 'w') as file:
            file.write(FLIGHT_FIELDS)
            for key, value in sorted(flights.items()):
                print(value, file=file)
                valid_flights += 1

        log.info('written file: %s', flight_file)

    except EnvironmentError:
        log.error('could not write file: %s', flight_file)

    # if airport stand data was provided
    if len(airport_stands_df):
        # Output the APDS position data
        positions_file = output_files[1]
        try:
            with open(positions_file, 'w') as file:
                file.write(POSITION_FIELDS)
                for key, value in sorted(flights.items()):
                    for event in sorted(value.positions):
                        print(event, file=file)

            log.info('written file: %s', positions_file)

        except EnvironmentError:
            log.error('could not write file: %s', positions_file)

    # Output the APDS event data
    event_file = output_files[2]
    try:
        with open(event_file, 'w') as file:
            file.write(FLIGHT_EVENT_FIELDS)
            for key, value in sorted(flights.items()):
                for event in sorted(value.events):
                    print(event, file=file)

        log.info('written file: %s', event_file)

    except EnvironmentError:
        log.error('could not write file: %s', event_file)
        return errno.EACCES

    log.info('apds conversion complete for %s flights on %s',
             valid_flights, start_date)

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: convert_apt_data.py <apds_filename> [stands_filename]')
        sys.exit(errno.EINVAL)

    # Get the stands_filename, if supplied
    stands_filename = ''
    if len(sys.argv) >= 3:
        stands_filename = sys.argv[2]

    error_code = convert_apds_data(sys.argv[1], stands_filename)
    if error_code:
        sys.exit(error_code)
