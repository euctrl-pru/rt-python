# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Functions to create names of Eurocontrol PRU refined trajectory files.
"""

from pru.trajectory_fields import CSV_FILE_EXTENSION, JSON_FILE_EXTENSION, \
    compact_date, iso8601_previous_day, create_iso8601_csv_filename

# Default file names
DEFAULT_AIRPORTS_FILENAME = 'airports.csv'
""" A file containing IATA and ICAO airport codes for convert_airport_ids.py. """

DEFAULT_STANDS_FILENAME = 'stands_EGLL.csv'
""" A file airport stand positions for convert_apt_data.py. """

DEFAULT_AIRSPACES_FILENAME = 'ES_428.geojson'
""" A file containing elementary airspace sectors. """

# Data file sources
APDS = "apds"
CPR = 'cpr'
FR24 = 'fr24'

# Sourcs data types
FLIGHTS = 'flights'
EVENTS = 'events'
POSITIONS = 'positions'

# Product file sources
CPR_FR24 = 'cpr_fr24'
APDS_CPR_FR24 = 'apds_cpr_fr24'

# Product data types
FLEET_DATA = 'fleet_data'
ERROR_METRICS = 'error_metrics'
MATCHING_IDS = 'matching_ids'
TRAJECTORIES = 'trajectories'
TRAJ_METRICS = 'traj_metrics'
REF_POSITIONS = 'ref_positions'

INTERSECTIONS = 'intersections'
SECTOR = 'sector'
AIRPORT = 'airport'
USER = 'user'

SECTOR_INTERSECTIONS = 'sector_intersections'
AIRPORT_INTERSECTIONS = 'airport_intersections'
USER_INTERSECTIONS = 'user_intersections'

# Misc
PREV_DAY = 'prev_day'
NEW_CPR_FR24 = 'new_cpr_fr24'
RAW_CPR_FR24 = 'raw_cpr_fr24'
RAW = 'raw'
NEW = 'new'
REF = 'ref'
IDS = 'ids'
IATA = 'iata'

ORIGINAL_CPR_FILE_PREFIX = '1.'
ORIGINAL_CPR_FILE_SUFFIX = '1001tacop104ARCHIVED_OPLOG_ALL_CPR.gz'

ORIGINAL_FR24_FLIGHT_FILE_PREFIX = 'FR24_ADSB_DATA_FLIGHTS_'
ORIGINAL_FR24_POINTS_FILE_PREFIX = 'FR24_ADSB_DATA_POINTS_'


def create_original_cpr_filename(date):
    """ Create a original CPR filename from a valid ISO8601 date. """
    return ''.join([ORIGINAL_CPR_FILE_PREFIX, compact_date(date),
                    ORIGINAL_CPR_FILE_SUFFIX])


def create_original_fr24_data_filenames(date):
    """ Create original FR24 filenames from a valid ISO8601 date. """
    return [create_iso8601_csv_filename(ORIGINAL_FR24_FLIGHT_FILE_PREFIX, date,
                                        is_bz2=True),
            create_iso8601_csv_filename(ORIGINAL_FR24_POINTS_FILE_PREFIX, date,
                                        is_bz2=True)]


def create_flights_filename(process, datestring):
    """
    Create a filename string for a flights file.
    Note: process is the name of the process that created the flights file:
    CPR, FR24, CPR_FR24, etc.
    """
    return '_'.join([process, FLIGHTS, datestring + CSV_FILE_EXTENSION])


def create_events_filename(process, datestring):
    """
    Create a filename string for a events file.
    Note: process is the name of the process that created the flights file:
    CPR, FR24, CPR_FR24, etc.
    """
    return '_'.join([process, EVENTS, datestring + CSV_FILE_EXTENSION])


def create_positions_filename(process, datestring):
    """
    Create a filename string for a positions file.
    Note: process is the name of the process that created the positions file:
    CPR, FR24, CPR_FR24, etc.
    """
    return '_'.join([process, POSITIONS, datestring + CSV_FILE_EXTENSION])


def create_ref_positions_filename(process, datestring):
    """
    Create a filename string for a ref positions file.
    Note: process is the name of the process that created the original positions
    file: CPR, FR24, CPR_FR24, etc.
    """
    return '_'.join([process, REF_POSITIONS, datestring + CSV_FILE_EXTENSION])


def create_raw_positions_filename(process, datestring):
    """
    Create a filename string for a raw positions file.
    Note: process is the name of the process that created the original positions
    file: CPR, FR24, CPR_FR24, etc.
    """
    return '_'.join([RAW, create_positions_filename(process, datestring)])


def create_trajectories_filename(process, datestring):
    """ Create a filename string for a trajectories file. """
    return '_'.join([process, TRAJECTORIES, datestring + JSON_FILE_EXTENSION])


def create_error_metrics_filename(process, datestring):
    """ Create a filename string for a position error metrics file. """
    return '_'.join([process, ERROR_METRICS, datestring + CSV_FILE_EXTENSION])


def create_trajectory_metrics_filename(process, datestring):
    """ Create a filename string for a trajectory metrics file. """
    return '_'.join([process, TRAJ_METRICS, datestring + CSV_FILE_EXTENSION])


def create_convert_cpr_filenames(datestring):
    """ Create the list of filenames output by convert_cpr_data.py. """
    return [create_flights_filename(CPR, datestring),
            create_events_filename(CPR, datestring),
            create_raw_positions_filename(CPR, datestring)]


def create_convert_fr24_filenames(datestring):
    """
    Create the list of filenames output by convert_fr24_data.py.
    Note: the flights filename is pre-pended by 'iata_'
    """
    return ['_'.join([IATA, create_flights_filename(FR24, datestring)]),
            create_raw_positions_filename(FR24, datestring)]


def create_fleet_data_filename(datestring):
    """ Create a filename string for a fleet data file. """
    return ''.join([FLEET_DATA, '_', datestring, CSV_FILE_EXTENSION])


def create_apds_flights_filename(from_date, to_date):
    """ Create a filename string for a apds flights file. """
    return '_'.join([APDS, FLIGHTS, from_date, to_date + CSV_FILE_EXTENSION])


def create_apds_events_filename(from_date, to_date):
    """ Create a filename string for a apds events file. """
    return '_'.join([APDS, EVENTS, from_date, to_date + CSV_FILE_EXTENSION])


def create_apds_positions_filename(from_date, to_date):
    """ Create a filename string for a apds positions file. """
    return '_'.join([APDS, POSITIONS, from_date, to_date + CSV_FILE_EXTENSION])


def create_convert_apds_filenames(from_date, to_date):
    """ Create the list of filenames output by convert_apt_data.py. """
    return [create_apds_flights_filename(from_date, to_date),
            create_apds_positions_filename(from_date, to_date),
            create_apds_events_filename(from_date, to_date)]


def create_daily_filenames(datestring, process=CPR_FR24):
    """ Create the list of filenames for a day. """
    return [create_flights_filename(process, datestring),
            create_positions_filename(process, datestring),
            create_events_filename(process, datestring)]


def create_clean_position_data_filenames(process, datestring):
    """
    Create the list of filenames output by clean_position_data.py.
    """
    return [create_positions_filename(process, datestring),
            create_error_metrics_filename(process, datestring)]


def create_analyse_position_data_filenames(process, datestring,
                                           distance_tolerance, method):
    """
    Create the list of filenames output by analyse_position_data.py.
    """
    tolerance_string = str(distance_tolerance).replace('.', '')
    traj_filename = '_'.join([method, tolerance_string,
                              create_trajectories_filename(process, datestring)])
    metrics_filename = '_'.join([method, tolerance_string,
                                 create_trajectory_metrics_filename(process, datestring)])
    return [traj_filename, metrics_filename]


def create_match_cpr_adsb_input_filenames(datestring):
    """ Create the list of filenames for match_cpr_adsb_trajectories.py. """
    return [create_flights_filename(CPR, datestring),
            create_flights_filename(FR24, datestring),
            create_positions_filename(CPR, datestring),
            create_positions_filename(FR24, datestring)]


def create_matching_ids_filename(process, datestring):
    """
    Create a filename string for a matching ids file.
    Note: process is the name of the process that created the flights file:
    CPR or FR24.
    """
    return '_'.join([process, MATCHING_IDS, datestring + CSV_FILE_EXTENSION])


def create_match_cpr_adsb_output_filenames(datestring):
    """ Create the list of filenames for match_cpr_adsb_trajectories.py. """
    return [create_matching_ids_filename(CPR, datestring),
            create_matching_ids_filename(FR24, datestring)]


def create_merge_cpr_adsb_input_filenames(datestring):
    """ Create the list of filenames for merge_cpr_adsb_trajectories.py. """
    return create_match_cpr_adsb_output_filenames(datestring) + \
        create_match_cpr_adsb_input_filenames(datestring) + \
        [create_events_filename(CPR, datestring)]


def create_merge_cpr_adsb_output_filenames(datestring):
    """ Create the list of filenames output by merge_cpr_adsb_trajectories.py. """
    return [create_flights_filename(CPR_FR24, datestring),
            create_raw_positions_filename(CPR_FR24, datestring),
            create_events_filename(CPR_FR24, datestring)]


def create_match_consecutive_day_input_filenames(datestring):
    """ Create the list of filenames for match_consecutive_day_trajectories.py. """
    prev_datestring = iso8601_previous_day(datestring)
    return [create_flights_filename(CPR_FR24, prev_datestring),
            create_flights_filename(CPR_FR24, datestring),
            create_positions_filename(CPR_FR24, prev_datestring),
            create_positions_filename(CPR_FR24, datestring)]


def create_merge_consecutive_day_input_filenames(datestring):
    """ Create the list of filenames for merge_consecutive_day_trajectories.py. """
    prev_datestring = iso8601_previous_day(datestring)
    return [create_matching_ids_filename(PREV_DAY, datestring)] + \
        create_match_consecutive_day_input_filenames(datestring) + \
        [create_events_filename(CPR_FR24, prev_datestring),
         create_events_filename(CPR_FR24, datestring)]


def create_merge_consecutive_day_output_filenames(datestring):
    """ Create the list of filenames output by merge_consecutive_day_trajectories.py. """
    NEW_CPR_FR24 = '_'.join([NEW, CPR_FR24])
    prev_datestring = iso8601_previous_day(datestring)
    return [create_flights_filename(NEW_CPR_FR24, prev_datestring),
            create_flights_filename(NEW_CPR_FR24, datestring),
            create_positions_filename(NEW_CPR_FR24, prev_datestring),
            create_positions_filename(NEW_CPR_FR24, datestring),
            create_events_filename(NEW_CPR_FR24, prev_datestring),
            create_events_filename(NEW_CPR_FR24, datestring)]


def create_match_apds_input_filenames(from_date, to_date, datestring):
    """ Create the list of filenames for match_apt_trajectories.py. """
    return [create_flights_filename(CPR_FR24, datestring),
            create_apds_flights_filename(from_date, to_date),
            create_events_filename(CPR_FR24, datestring),
            create_apds_events_filename(from_date, to_date)]


def create_merge_apds_input_filenames(from_date, to_date, datestring):
    """ Create the list of filenames for merge_apt_trajectories.py. """
    return [create_matching_ids_filename(APDS, datestring),
            create_positions_filename(CPR_FR24, datestring),
            create_apds_positions_filename(from_date, to_date),
            create_events_filename(CPR_FR24, datestring),
            create_apds_events_filename(from_date, to_date)]


def create_merge_apds_output_filenames(datestring):
    """ Create the list of filenames output by merge_apt_trajectories.py. """
    return [create_positions_filename(APDS_CPR_FR24, datestring),
            create_events_filename(APDS_CPR_FR24, datestring)]
