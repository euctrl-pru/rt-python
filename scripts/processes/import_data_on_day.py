#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Imports, refines and merges CPR and FR24 data for a given day.
"""

import sys
import errno
import subprocess
import gc

from pru.env.env_constants import PROJECT_HOME
from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import DEFAULT_AIRPORTS_FILENAME, CPR, FR24, CPR_FR24, \
    create_raw_positions_filename, create_flights_filename, \
    create_original_cpr_filename, create_convert_cpr_filenames, \
    create_original_fr24_data_filenames, create_convert_fr24_filenames, \
    create_fleet_data_filename, create_clean_position_data_filenames, \
    create_match_cpr_adsb_input_filenames, create_match_cpr_adsb_output_filenames, \
    create_merge_cpr_adsb_input_filenames, create_merge_cpr_adsb_output_filenames

from pru.filesystem.data_store_operations import get_unprocessed, get_airports, \
    put_processed, SOURCES_CPR, SOURCES_FR24, PRODUCTS_FLEET, PRODUCTS, ERROR_METRICS, \
    SOURCES, SOURCES_MERGED_DAILY_CPR_FR24, SOURCES_MERGED_DAILY_CPR_FR24_IDS

from pru.trajectory_cleaning import DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from apps.convert_fr24_data import convert_fr24_data
from apps.convert_airport_ids import convert_airport_ids
from apps.extract_fleet_data import extract_fleet_data
from apps.match_cpr_adsb_trajectories import match_cpr_adsb_trajectories
from apps.merge_cpr_adsb_trajectories import merge_cpr_adsb_trajectories

from pru.logger import logger

log = logger(__name__)

CLEAN_POSITION_DATA_APP = PROJECT_HOME + '/apps/clean_position_data.py'
""" The clean_position_data application. """
CONVERT_CPR_DATA_APP = PROJECT_HOME + '/apps/convert_cpr_data.py'
""" The convert_cpr_data application. """


def clean_raw_positions_data(source, date, max_speed=DEFAULT_MAX_SPEED,
                             distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Call the clean_position_data function as a process to run in parallel.

    Parameters
    ----------
    source: string
        The source of the positions data: CPR, FR24 or CPR_FR24

    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    max_speed: string
        The maximum ground speed permitted between adjacent positions [Knots],
        default: 750 Knots.

    distance_accuracy: string
        The maximum distance between positions at the same time [Nautical Miles],
        default: 0.25 NM.

    Returns
    -------
    A child process.

    """
    raw_filename = create_raw_positions_filename(source, date)
    log.info(f'Cleaning data in: {raw_filename}')
    return subprocess.Popen(['python', CLEAN_POSITION_DATA_APP, raw_filename,
                             str(max_speed), str(distance_accuracy)],
                            stdout=subprocess.PIPE, universal_newlines=True)


def convert_cpr_data_on_day(date):
    """
    Call the convert_cpr_data function as a process to run in parallel.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
    A child process.

    """
    cpr_filename = create_original_cpr_filename(date)

    return subprocess.Popen(['python', CONVERT_CPR_DATA_APP, cpr_filename],
                            stdout=subprocess.PIPE, universal_newlines=True)


def convert_fr24_data_on_day(date):
    """
    Call the convert_fr24_data function for the date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    """
    filenames = create_original_fr24_data_filenames(date)
    error_code = convert_fr24_data(filenames)
    if error_code:
        sys.exit(error_code)


def write_clean_positions_data(source, date):
    """
    Write the cleaned position data and error metrics to the Google bucket.

    Parameters
    ----------
    source: string
        The source of the positions data: CPR, FR24 or CPR_FR24

    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    """
    filenames = create_clean_position_data_filenames(source, date)

    source_path = SOURCES_MERGED_DAILY_CPR_FR24 \
        if (source == CPR_FR24) else '/'.join([SOURCES, source])
    put_processed(source_path, filenames[:1])

    errors_path = '/'.join([PRODUCTS, ERROR_METRICS, source])
    put_processed(errors_path, filenames[1:])


def process_fr24_flights(date, airports_filename):
    """
    Convert the IATA airport ids in an FR24 flight file to ICAO ids.

    Also extracts aircraft fleet data from an FR24 flight file.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    airports_filename: string
        The name of a file containing airport codes for IATA to ICAO conversion.

    """
    get_airports(airports_filename, '.')

    iata_filename, _ = create_convert_fr24_filenames(date)
    error_code = convert_airport_ids(iata_filename, airports_filename)
    if error_code:
        sys.exit(error_code)

    put_processed(SOURCES_FR24, [create_flights_filename(FR24, date)])

    error_code = extract_fleet_data(iata_filename)
    if error_code:
        sys.exit(error_code)

    put_processed(PRODUCTS_FLEET, [create_fleet_data_filename(date)])


def merge_cpr_and_fr24_data(date):
    """
    Merge the CPR and FR24 data for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    """
    match_filenames = create_match_cpr_adsb_input_filenames(date)
    error_code = match_cpr_adsb_trajectories(match_filenames)
    if error_code:
        sys.exit(error_code)
    gc.collect()

    merge_filenames = create_merge_cpr_adsb_input_filenames(date)
    error_code = merge_cpr_adsb_trajectories(merge_filenames)
    if error_code:
        sys.exit(error_code)


def import_data_on_day(date, max_speed=DEFAULT_MAX_SPEED,
                       distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Import, refine and merge the CPR and FR24 data for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    max_speed: string
        The maximum ground speed permitted between adjacent positions [Knots],
        default: 750 Knots.

    distance_accuracy: string
        The maximum distance between positions at the same time [Nautical Miles],
        default: 0.25 NM.

    """
    if is_valid_iso8601_date(date):

        log.info(f'Getting data for date: {date}')

        # convert the FR24 data
        # Note: needs over 13GB memory if run with convert_cpr_data.
        get_unprocessed(FR24, date, '.')
        convert_fr24_data_on_day(date)
        gc.collect()

        # Clean the FR24 data in parallel
        procs = []
        procs.append(clean_raw_positions_data(FR24, date,
                                              max_speed, distance_accuracy))

        # convert the CPR data in parallel
        get_unprocessed(CPR, date, '.')
        cpr_proc = convert_cpr_data_on_day(date)

        # write the converted FR24 data to the Google bucket
        put_processed(SOURCES_FR24, create_convert_fr24_filenames(date))

        process_fr24_flights(date, DEFAULT_AIRPORTS_FILENAME)
        gc.collect()

        # Wait for CPR conversion to finish
        out, err = cpr_proc.communicate()
        print(out)
        gc.collect()

        # Clean the CPR and FR24 data in parallel
        procs.append(clean_raw_positions_data(CPR, date,
                                              max_speed, distance_accuracy))

        # write the converted CPR data to the Google bucket
        put_processed(SOURCES_CPR, create_convert_cpr_filenames(date))

        # Wait for the CPR and FR24 cleaning tasks
        for proc in procs:
            out, err = proc.communicate()
            print(out)

        # write the CPR and FR24 positions to the Google bucket
        write_clean_positions_data(CPR, date)
        write_clean_positions_data(FR24, date)
        gc.collect()

        merge_cpr_and_fr24_data(date)
        gc.collect()

        # Clean the merged positions
        proc = clean_raw_positions_data(CPR_FR24, date,
                                        max_speed, distance_accuracy)

        # put the merged CPR and FR24 data to the Google bucket
        put_processed(SOURCES_MERGED_DAILY_CPR_FR24_IDS,
                      create_match_cpr_adsb_output_filenames(date))
        put_processed(SOURCES_MERGED_DAILY_CPR_FR24,
                      create_merge_cpr_adsb_output_filenames(date))

        # Wait for cleaning to finish
        out, err = proc.communicate()
        print(out)

        # put the merged CPR and FR24 positions to the Google bucket
        write_clean_positions_data(CPR_FR24, date)

    else:
        log.error(f'invalid date: {date}')
        return errno.EINVAL

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: import_data_on_day.py <date>'
              ' [max_speed] [distance_accuracy]')
        sys.exit(errno.EINVAL)

    max_speed = DEFAULT_MAX_SPEED
    if len(sys.argv) >= 3:
        max_speed = float(sys.argv[2])

    distance_accuracy = DEFAULT_DISTANCE_ACCURACY
    if len(sys.argv) >= 4:
        distance_accuracy = float(sys.argv[3])

    error_code = import_data_on_day(sys.argv[1], max_speed, distance_accuracy)
    if error_code:
        sys.exit(error_code)
