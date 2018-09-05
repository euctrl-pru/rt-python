#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Contains Celery task definitions for the work required to complete
processing of original input data files into quality reports and refined
trajectories.
"""

import os
import gc
import subprocess
from pru.env.env_constants import DATA_HOME, UPLOAD_DIR
from pru.filesystem.data_store_operations import SOURCES_CPR, SOURCES_FR24, SOURCES_APDS, \
    FLEET_DATA_DIR, \
    SOURCES, MERGED, DAILY_CPR_FR24, PRODUCTS, PRODUCTS_FLEET, AIRPORTS, \
    SOURCES_MERGED_DAILY_CPR_FR24, SOURCES_MERGED_DAILY_CPR_FR24_IDS, \
    SOURCES_MERGED_OVERNIGHT_CPR_FR24, SOURCES_MERGED_OVERNIGHT_CPR_FR24_IDS, \
    PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT, PRODUCTS_INTERSECTIONS_SECTOR, \
    PRODUCTS_INTERSECTIONS_AIRPORT, PRODUCTS_INTERSECTIONS_USER, \
    SOURCES_MERGED_APDS_CPR_FR24, SOURCES_MERGED_APDS_CPR_FR24_IDS, \
    path_exists, get_unprocessed, put_processed, get_processed, \
    get_airports, get_apds, get_stands, AIRPORTS_STANDS
from pru.trajectory_fields import iso8601_previous_day, split_dual_date, \
    read_iso8601_date_string, CSV_FILE_EXTENSION, JSON_FILE_EXTENSION
from pru.trajectory_files import DEFAULT_AIRPORTS_FILENAME, DEFAULT_STANDS_FILENAME, \
    APDS, CPR, FR24, CPR_FR24, PREV_DAY, NEW, REF, RAW_CPR_FR24, ERROR_METRICS, \
    TRAJECTORIES, TRAJ_METRICS, REF_POSITIONS, \
    SECTOR_INTERSECTIONS, AIRPORT_INTERSECTIONS, USER_INTERSECTIONS, \
    create_original_cpr_filename, create_original_fr24_data_filenames, \
    create_flights_filename, create_positions_filename, \
    create_convert_cpr_filenames, create_convert_fr24_filenames, \
    create_fleet_data_filename, create_raw_positions_filename, \
    create_trajectories_filename, create_ref_positions_filename, \
    create_clean_position_data_filenames, create_analyse_position_data_filenames, \
    create_match_cpr_adsb_input_filenames, create_match_cpr_adsb_output_filenames, \
    create_merge_cpr_adsb_input_filenames, create_merge_cpr_adsb_output_filenames, \
    create_match_consecutive_day_input_filenames, create_matching_ids_filename, \
    create_merge_consecutive_day_input_filenames, \
    create_merge_consecutive_day_output_filenames, \
    create_convert_apds_filenames, create_daily_filenames, \
    create_match_apds_input_filenames, \
    create_merge_apds_input_filenames, create_merge_apds_output_filenames
from pru.trajectory_cleaning import DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from pru.trajectory_analysis import DEFAULT_ACROSS_TRACK_TOLERANCE, MOVING_AVERAGE_SPEED, \
    DEFAULT_MOVING_MEDIAN_SAMPLES, DEFAULT_MOVING_AVERAGE_SAMPLES, \
    DEFAULT_SPEED_MAX_DURATION
from pru.trajectory_interpolation import DEFAULT_STRAIGHT_INTERVAL, DEFAULT_TURN_INTERVAL
from pru.trajectory_airport_intersections import DEFAULT_RADIUS, DEFAULT_DISTANCE_TOLERANCE

from apps.convert_cpr_data import convert_cpr_data
from apps.convert_fr24_data import convert_fr24_data
from apps.convert_airport_ids import convert_airport_ids
from apps.extract_fleet_data import extract_fleet_data
from apps.clean_position_data import clean_position_data
from apps.convert_apt_data import convert_apds_data

from apps.match_cpr_adsb_trajectories import match_cpr_adsb_trajectories
from apps.merge_cpr_adsb_trajectories import merge_cpr_adsb_trajectories
from apps.match_consecutive_day_trajectories import match_consecutive_day_trajectories
from apps.merge_consecutive_day_trajectories import merge_consecutive_day_trajectories
from apps.match_apt_trajectories import match_apds_trajectories
from apps.merge_apt_trajectories import merge_apds_trajectories

from apps.analyse_position_data import analyse_position_data
from apps.interpolate_trajectories import interpolate_trajectories

from apps.find_sector_intersections import find_sector_intersections
from apps.find_airport_intersections import find_airport_intersections, \
    DEFAULT_MOVEMENTS_AIRPORTS_FILENAME
from apps.find_user_airspace_intersections import find_user_airspace_intersections

from pru.logger import logger

log = logger(__name__)

DEFAULT_LOGGING_COUNT = 5000
""" The default number of flights between each log message. """


def clean_raw_positions_data(source, date, max_speed=DEFAULT_MAX_SPEED,
                             distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Clean the refined CPR positions file for the given date.

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
        True if succesful, False otherwise.

    """
    raw_filename = create_raw_positions_filename(source, date)
    if clean_position_data(raw_filename, max_speed, distance_accuracy):
        return False

    os.remove(raw_filename)  # delete the raw positions file

    filenames = create_clean_position_data_filenames(source, date)

    # Put the error metrics file first so that it can be deleted
    errors_path = '/'.join([PRODUCTS, ERROR_METRICS, source])
    if not put_processed(errors_path, filenames[1:]):
        return False

    os.remove(filenames[1])  # delete the error metrics file

    source_path = '/'.join([SOURCES, MERGED, DAILY_CPR_FR24]) \
        if (source == CPR_FR24) else '/'.join([SOURCES, source])
    return put_processed(source_path, filenames[:1])


def convert_cpr_file(date):
    """
    Converts a CPR file for the given date into PRU format.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    get_unprocessed(CPR, date)
    cpr_filename = '/'.join([UPLOAD_DIR, CPR, create_original_cpr_filename(date)])

    log.debug("converting cpr data from file: %s", cpr_filename)
    if convert_cpr_data(cpr_filename):
        return False
    gc.collect()

    os.remove(cpr_filename)  # delete the uploaded CPR file

    return put_processed(SOURCES_CPR, create_convert_cpr_filenames(date))


def convert_fr24_date(date):
    """
    Converts a FR24 ADS-B data for the given date into PRU format.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    get_unprocessed(FR24, date)
    filenames = ['/'.join([UPLOAD_DIR, FR24, file])
                 for file in create_original_fr24_data_filenames(date)]

    if convert_fr24_data(filenames):
        return False
    gc.collect()

    # delete the uploaded FR24 files
    [os.remove(file_path) for file_path in filenames]

    return put_processed(SOURCES_FR24, create_convert_fr24_filenames(date))


def convert_airport_codes(date, airports_filename=DEFAULT_AIRPORTS_FILENAME):
    """
    Convert FR24 IATA departure and destination airport codes to ICAO codes.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    airports_filename: string
        The name of a file containing airport codes for IATA to ICAO conversion,
        default: airports.csv

    Returns
    -------
        True if succesful, False otherwise.

    """
    iata_filename, _ = create_convert_fr24_filenames(date)
    if (airports_filename == DEFAULT_AIRPORTS_FILENAME):
        log.debug("Using the default airports file, %s", "airports.csv")

    get_airports(airports_filename)
    airports_file_path = '/'.join([DATA_HOME, AIRPORTS, airports_filename])

    if convert_airport_ids(iata_filename, airports_file_path):
        return False
    gc.collect()

    os.remove(iata_filename)  # delete the iata flights file

    return put_processed(SOURCES_FR24, [create_flights_filename(FR24, date)])


def extract_fleet_date(date):
    """
    Extract aircraft fleet data from an FR24 flights file for the fleet database.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    if extract_fleet_data(create_flights_filename(FR24, date)):
        # if the normal flights file does not exist yet, try the IATA file
        iata_filename, _ = create_convert_fr24_filenames(date)
        if extract_fleet_data(iata_filename):
            return False
    gc.collect()

    fleet_filename = create_fleet_data_filename(date)
    copied_ok = put_processed(PRODUCTS_FLEET, [fleet_filename])
    if copied_ok:
        new_filepath = '/'.join([FLEET_DATA_DIR, fleet_filename])
        os.rename(fleet_filename, new_filepath)
        # os.remove(fleet_filename)  # delete the fleet data file

    return copied_ok


def match_cpr_adsb_trajectories_on(date):
    """
    Match refined CPR and FR24 ADS-B data for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    filenames = create_match_cpr_adsb_input_filenames(date)
    if match_cpr_adsb_trajectories(filenames):
        return False
    gc.collect()

    return put_processed(SOURCES_MERGED_DAILY_CPR_FR24_IDS,
                         create_match_cpr_adsb_output_filenames(date))


def merge_cpr_adsb_trajectories_on(date):
    """
    Merge refined CPR and FR24 ADS-B data for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    filenames = create_merge_cpr_adsb_input_filenames(date)
    if merge_cpr_adsb_trajectories(filenames):
        return False
    gc.collect()

    # delete the source input files
    [os.remove(file_path) for file_path in filenames]

    return put_processed(SOURCES_MERGED_DAILY_CPR_FR24,
                         create_merge_cpr_adsb_output_filenames(date))


def match_previous_days_flights(date):
    """
    Match merged CPR and FR24 ADS-B data for the given date,
    with merged CPR and FR24 ADS-B data for the previous day.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    # Get the previous days files from the overnight bucket, if not available locally
    merge_files = create_merge_consecutive_day_input_filenames(date)
    if not path_exists(merge_files[1]) or \
            not path_exists(merge_files[3]) or \
            not path_exists(merge_files[5]):
        log.debug("Getting files %s, %s, %s", merge_files[1], merge_files[3], merge_files[5])
        if not get_processed(SOURCES_MERGED_OVERNIGHT_CPR_FR24, merge_files[1::2]):
            log.error('Previous days files not found in overnight_cpr_fr24 bucket')
            return False

    # Get the current days files from the daily bucket, if not available locally
    if not path_exists(merge_files[2]) or \
            not path_exists(merge_files[4]) or \
            not path_exists(merge_files[6]):
        log.debug("Getting files %s, %s, %s", merge_files[2], merge_files[4], merge_files[6])
        if not get_processed(SOURCES_MERGED_DAILY_CPR_FR24, merge_files[2::2]):
            log.error('Current days files not found in daily_cpr_fr24 bucket')
            return False

    filenames = create_match_consecutive_day_input_filenames(date)
    if match_consecutive_day_trajectories(filenames):
        return False
    gc.collect()

    prev_ids_filename = create_matching_ids_filename(PREV_DAY, date)
    return put_processed(SOURCES_MERGED_OVERNIGHT_CPR_FR24_IDS, [prev_ids_filename])


def merge_previous_days_data(date):
    """
    Merge merged CPR and FR24 ADS-B data for the given date,
    with merged CPR and FR24 ADS-B data for the previous day.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    filenames = create_merge_consecutive_day_input_filenames(date)
    if merge_consecutive_day_trajectories(filenames):
        return False
    gc.collect()

    # rename output filenames to input files
    new_files = create_merge_consecutive_day_output_filenames(date)
    log.debug("Moving files: %s", str(new_files))
    [subprocess.run(['mv', file, file[len(NEW) + 1:]]) for file in new_files]

    # rename the previous days positions filename to raw_...
    raw_positions_filename = filenames[3].replace(CPR_FR24, RAW_CPR_FR24)
    os.rename(filenames[3], raw_positions_filename)
    filenames[3] = raw_positions_filename

    copied_ok = put_processed(SOURCES_MERGED_OVERNIGHT_CPR_FR24, filenames[1:])
    if copied_ok:
        [os.remove(file_path) for file_path in filenames[:3]]
        # Don't remove the raw positions file
        [os.remove(file_path) for file_path in filenames[4:]]

    return copied_ok


def clean_overnight_cpr_fr24_positions(date, max_speed=DEFAULT_MAX_SPEED,
                                       distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Clean merged CPR and FR24 ADS-B data after merging with the 'next day'.

    Parameters
    ----------
    date: string
        The date (of the previous day!) in ISO8601 format, e.g. 2017-08-16

    max_speed: string
        The maximum ground speed permitted between adjacent positions [Knots],
        default: 750 Knots.

    distance_accuracy: string
        The maximum distance between positions at the same time [Nautical Miles],
        default: 0.25 NM.

    Returns-
    -------
        True if succesful, False otherwise.

    """
    date = iso8601_previous_day(date)
    raw_filename = create_raw_positions_filename(CPR_FR24, date)

    # TODO this call is failing, investigate.
    if clean_position_data(raw_filename, max_speed, distance_accuracy):
        return False

    os.remove(raw_filename)  # delete the raw positions file

    # Put the error metrics file first
    filenames = create_clean_position_data_filenames(CPR_FR24, date)
    if not put_processed(SOURCES_MERGED_OVERNIGHT_CPR_FR24, filenames[:1]):
        return False

    if not put_processed(PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT, filenames[1:]):
        return False

    # delete the cleaned file and metrics file
    [os.remove(file_path) for file_path in filenames]

    return True


def analyse_positions_on_date(date, source=CPR_FR24, *,
                              distance_tolerance=DEFAULT_ACROSS_TRACK_TOLERANCE,
                              time_method=MOVING_AVERAGE_SPEED,
                              N=DEFAULT_MOVING_MEDIAN_SAMPLES,
                              M=DEFAULT_MOVING_AVERAGE_SAMPLES,
                              max_duration=DEFAULT_SPEED_MAX_DURATION,
                              logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    Analyse refined CPR and FR24 ADS-B data for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    source: string
        The data to analyse, default cpr_fr24

    distance_tolerance: float
        The maximum across track distance[Nautical Miles], default: 0.25 NM.

    time_method: string
        The time analysis method, default 'lm'.

    N : integer
        The number of samples to consider for the speed moving median filter, default 5.

    M : integer
        The number of samples to consider for the speed moving average filter, default 5.

    max_duration: float
        The maximum time between points to smooth when calculating speed, default 120 [Seconds].

    logging_msg_count : integer
        The number of analysed flights between each log message.

    Returns
    -------
        True if succesful, False otherwise.

    """
    positions_filename = create_positions_filename(source, date)

    source_path = SOURCES_MERGED_OVERNIGHT_CPR_FR24 if (source == CPR_FR24) else \
        '/'.join([SOURCES, source])
    get_processed(source_path, [positions_filename])

    log.info("Analysing position data for file %s", positions_filename)
    if analyse_position_data(positions_filename, distance_tolerance, time_method):
        return False
    gc.collect()

    filenames = create_analyse_position_data_filenames(source, date,
                                                       distance_tolerance, time_method)

    # Put the traj metrics file first so that it can be deleted
    metrics_path = '/'.join([PRODUCTS, TRAJ_METRICS, source])
    if not put_processed(metrics_path, filenames[1:]):
        return False

    os.remove(filenames[1])  # delete the traj metrics file

    output_path = '/'.join([PRODUCTS, TRAJECTORIES, source])
    return put_processed(output_path, filenames[:1])


def interpolate_trajectory_file(trajectory_filename, source=CPR_FR24,
                                straight_interval=DEFAULT_STRAIGHT_INTERVAL,
                                turn_interval=DEFAULT_TURN_INTERVAL,
                                logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    Interpolate a trajectories file for the given date.

    Parameters
    ----------
    trajectory_filename: string
        The trajectory filename.

    source: string
        The data to interpolate, default cpr_fr24

    straight_interval: float
        The time interval between points on straight legs.

    turn_interval: float
        The time interval between points around turns.

    Returns
    -------
        True if succesful, False otherwise.

    """
    source_path = '/'.join([PRODUCTS, TRAJECTORIES, source])
    get_processed(source_path, [trajectory_filename])

    log.debug("Interpolating trajectories for file %s", trajectory_filename)
    if interpolate_trajectories(trajectory_filename, straight_interval,
                                turn_interval, logging_msg_count):
        return False
    gc.collect()

    os.remove(trajectory_filename)  # delete the trajectory file

    output_filename = trajectory_filename.replace(TRAJECTORIES, REF_POSITIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)

    output_path = '/'.join([PRODUCTS, REF_POSITIONS, source])
    return put_processed(output_path, [output_filename])


def refine_apds_file(apds_filename, stands_filename=DEFAULT_STANDS_FILENAME):
    """
    Converts an APDS file into PRU format flights, positions and events files.

    Parameters
    ----------
    apds_filename: string
        The name of the APDS file,
        e.g.: FAC_APDS_FLIGHT_IR691_2017-08-01_2017-09-01.csv.bz2

    stands_filename: string
        The name of the airport stands file, default DEFAULT_STANDS_FILENAME.

        Note: it won't create a positions file if run with a empty stands_filename.

    Returns
    -------
        True if succesful, False otherwise.


    """
    # Get the files from the bucket
    get_apds(apds_filename)
    get_stands(stands_filename)

    apds_path_name = '/'.join([UPLOAD_DIR, APDS, apds_filename])
    stands_path_name = '/'.join([DATA_HOME, AIRPORTS_STANDS, stands_filename])

    log.info("Converting APDS data with stands file: %s", stands_filename)
    if convert_apds_data(apds_path_name, stands_path_name):
        return False
    gc.collect()

    os.remove(apds_path_name)  # delete the uploaded APDS file

    from_date, to_date = split_dual_date(apds_filename)
    return put_processed(SOURCES_APDS,
                         create_convert_apds_filenames(from_date, to_date))


def match_apds_trajectories_on_day(from_date, to_date, date):
    """
    Match refined APDS data with CPR and FR24 ADS-B data for the given date.

    Parameters
    ----------
    from_date: string
        The APDS start date in ISO8601 format, e.g. 2017-08-01

    to_date: string
        The APDS finish date in ISO8601 format, e.g. 2017-08-31

    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    apds_filenames = create_convert_apds_filenames(from_date, to_date)
    if not path_exists(apds_filenames[0]) or \
            not path_exists(apds_filenames[1]) or \
            not path_exists(apds_filenames[2]):
        log.debug("Getting apds files: %s", str(apds_filenames))
        if not get_processed(SOURCES_APDS, apds_filenames):
            log.error('APDS files not found in sources/apds bucket')
            return False

    day_filenames = create_daily_filenames(date)
    log.debug("Getting days files: %s", str(day_filenames))
    if not get_processed(SOURCES_MERGED_OVERNIGHT_CPR_FR24, day_filenames):
        log.error('Data files not found in overnight_cpr_fr24 bucket')
        return False

    filenames = create_match_apds_input_filenames(from_date, to_date, date)
    log.info("matching apds trajectories with files %s", str(filenames))
    if match_apds_trajectories(filenames):
        return False
    gc.collect()

    return put_processed(SOURCES_MERGED_APDS_CPR_FR24_IDS,
                         [create_matching_ids_filename(APDS, date)])


def merge_apds_trajectories_on_day(from_date, to_date, date):
    """
    Merge refined APDS data with CPR and FR24 ADS-B data for the given date.

    Parameters
    ----------
    from_date: string
        The APDS start date in ISO8601 format, e.g. 2017-08-01

    to_date: string
        The APDS finish date in ISO8601 format, e.g. 2017-08-31

    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    Returns
    -------
        True if succesful, False otherwise.

    """
    filenames = create_merge_apds_input_filenames(from_date, to_date, date)
    log.info("merging apds trajectories with files %s", str(filenames))
    if merge_apds_trajectories(filenames):
        return False
    gc.collect()

    # delete the source daily input files
    day_filenames = create_daily_filenames(date)
    [os.remove(file_path) for file_path in day_filenames[1:]]

    # rename the flights file to add APDS to the start
    apds_flight_filename = '_'.join([APDS, day_filenames[0]])
    os.rename(day_filenames[0], apds_flight_filename)
    ok = put_processed(SOURCES_MERGED_APDS_CPR_FR24, [apds_flight_filename])
    if ok:
        os.remove(apds_flight_filename)
    else:
        return False

    output_filenames = create_merge_apds_output_filenames(date)
    ok = put_processed(SOURCES_MERGED_APDS_CPR_FR24, output_filenames)
    if ok:  # delete the output files
        [os.remove(file_path) for file_path in output_filenames]

    return ok


def find_trajectory_sector_intersections(trajectory_filename, source=CPR_FR24,
                                         logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    """
    if not path_exists(trajectory_filename):
        source_path = '/'.join([PRODUCTS, TRAJECTORIES, source])
        log.debug("Getting trajectory file: %s", trajectory_filename)
        if not get_processed(source_path, [trajectory_filename]):
            log.error('Trajectory file not found in%s bucket', source_path)
            return False

    log.info("find_sector_intersections for: %s", trajectory_filename)
    if find_sector_intersections(trajectory_filename, logging_msg_count):
        return False

    output_filename = trajectory_filename.replace(TRAJECTORIES, SECTOR_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)

    intersections_path = '/'.join([PRODUCTS_INTERSECTIONS_SECTOR, source])
    return put_processed(intersections_path, [output_filename])


def find_trajectory_airport_intersections(trajectory_filename, source=CPR_FR24,
                                          radius=DEFAULT_RADIUS,
                                          airports_filename=DEFAULT_MOVEMENTS_AIRPORTS_FILENAME,
                                          distance_tolerance=DEFAULT_DISTANCE_TOLERANCE):
    """
    """
    if not path_exists(trajectory_filename):
        source_path = '/'.join([PRODUCTS, TRAJECTORIES, source])
        log.debug("Getting trajectory file: %s", trajectory_filename)
        if not get_processed(source_path, [trajectory_filename]):
            log.error('Trajectory file not found in %s bucket', source_path)
            return False

    date = read_iso8601_date_string(trajectory_filename, is_json=True)
    flights_filename = create_flights_filename(source, date)
    if not path_exists(flights_filename):
        source_path = SOURCES_MERGED_OVERNIGHT_CPR_FR24 \
            if (source == CPR_FR24) else '/'.join([SOURCES, source])
        if not get_processed(source_path, [flights_filename]):
            log.error('Flights file not found in %s bucket', source_path)
            return False

    get_airports(airports_filename, '.')

    log.info("find_sector_intersections for: %s and %s",
             flights_filename, trajectory_filename)
    if find_airport_intersections(flights_filename, trajectory_filename,
                                  radius, airports_filename, distance_tolerance):
        return False

    output_filename = trajectory_filename.replace(TRAJECTORIES, AIRPORT_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)

    intersections_path = '/'.join([PRODUCTS_INTERSECTIONS_AIRPORT, source])
    return put_processed(intersections_path, [output_filename])


def find_trajectory_user_airspace_intersections(trajectory_filename, source=CPR_FR24,
                                                logging_msg_count=DEFAULT_LOGGING_COUNT):
    """
    """
    if not path_exists(trajectory_filename):
        source_path = '/'.join([PRODUCTS, TRAJECTORIES, source])
        log.debug("Getting trajectory file: %s", trajectory_filename)
        if not get_processed(source_path, [trajectory_filename]):
            log.error('Trajectory file not found in %s bucket', source_path)
            return False

    log.info("find_user_airspace_intersections for: %s", trajectory_filename)
    if find_user_airspace_intersections(trajectory_filename, logging_msg_count):
        return False

    output_filename = trajectory_filename.replace(TRAJECTORIES, USER_INTERSECTIONS)
    output_filename = output_filename.replace(JSON_FILE_EXTENSION,
                                              CSV_FILE_EXTENSION)

    intersections_path = '/'.join([PRODUCTS_INTERSECTIONS_USER, source])
    return put_processed(intersections_path, [output_filename])
