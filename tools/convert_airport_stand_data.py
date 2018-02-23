#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Extract airport stand data from files supplied by the PRU.
"""

import sys
import csv
from enum import IntEnum, unique
from pru.trajectory_fields import dms2decimal

STAND_FIELDS = 'ICAO_ID,STAND_ID,LAT,LON\n'

INVALID_LATITUDE = -90.0
'Set the default Latitude to the South Pole and consider it as invalid'

DEFAULT_LONGITUDE = -180.0
'Set the default Latitude to the International Date Line'


@unique
class StandField(IntEnum):
    STAND_ID = 0
    LAT = 1
    LON = 2


def lat2decimal(input):
    """
    Convert a Latitude into decimal angle.
    """
    lat_degrees = int(input[0:2])
    lat_minutes = int(input[2:4])
    lat_seconds = float(input[4:-2])
    lat_negative = ('S' == input[-1])

    return dms2decimal(lat_degrees, lat_minutes, lat_seconds, lat_negative)


def lon2decimal(input):
    """
    Convert a Longitude into decimal angle.
    """
    lng_degrees = int(input[0:3])
    lng_minutes = int(input[3:5])
    lng_seconds = float(input[5:-2])
    lng_negative = ('W' == input[-1])

    return dms2decimal(lng_degrees, lng_minutes, lng_seconds, lng_negative)


class AptStand:
    'A class for reading, storing and outputting data for a airport stand'

    def __init__(self, apt_fields, airport):
        self.id = apt_fields[StandField.STAND_ID]
        self.airport_id = airport
        self.latitude = INVALID_LATITUDE
        self.longitude = DEFAULT_LONGITUDE
        if len(apt_fields) > 2:
            if apt_fields[StandField.LAT] and apt_fields[StandField.LON]:
                self.latitude = lat2decimal(apt_fields[StandField.LAT])
                self.longitude = lon2decimal(apt_fields[StandField.LON])

    def update(self, apt_fields):
        if len(apt_fields) > 2:
            if (self.latitude == INVALID_LATITUDE) and \
                    apt_fields[StandField.LAT] and apt_fields[StandField.LON]:
                self.latitude = lat2decimal(apt_fields[StandField.LAT])
                self.longitude = lon2decimal(apt_fields[StandField.LON])

    def __hash__(self):
        return hash(hash(self.id) ^ hash(self.latitude) ^ hash(self.longitude))

    def __eq__(self, other):
        return (self.id == other.id) \
            and (self.airport_id == other.airport_id) \
            and (self.latitude == other.latitude) \
            and (self.longitude == other.longitude)

    def __repr__(self):
        return '{},{},{:.8f},{:.8f}'.\
            format(self.airport_id, self.id, self.latitude, self.longitude)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('Usage: convert_airport_stand_data.py <airport_stands_filename>')
        sys.exit(2)

    filename = sys.argv[1]

    airport_id = filename[0:4]
    if len(sys.argv) >= 3:
        airport_id = sys.argv[2]

    print('airport:', airport_id)

    # A dict to hold the airport stands
    stands = {}

    # Read the file into stands
    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader, None)  # skip the headers
            for row in reader:
                stands.setdefault(row[StandField.STAND_ID],
                                  AptStand(row, airport_id)).update(row)

    except EnvironmentError:
        print('could not read file:', filename)
        sys.exit(2)

    # Write the stands into output_file
    output_file = 'stands_' + filename
    try:
        with open(output_file, 'w') as file:
            file.write(STAND_FIELDS)
            for key, value in sorted(stands.items()):
                if value.latitude > INVALID_LATITUDE:
                    print(value, file=file)

    except EnvironmentError:
        print('could not write file:', output_file)
