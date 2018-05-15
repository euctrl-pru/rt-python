#
# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Wraps tasks into higher level processes, e.g.: converting & cleaning to refining.
"""

import os
import scripts.tasks as tasks
from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import DEFAULT_AIRPORTS_FILENAME, CPR, FR24, CPR_FR24
from pru.filesystem.data_store_operations import REFINED_DIR
from pru.trajectory_cleaning import DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from pru.trajectory_analysis import DEFAULT_ACROSS_TRACK_TOLERANCE
from pru.trajectory_interpolation import DEFAULT_STRAIGHT_INTERVAL, DEFAULT_TURN_INTERVAL
from pru.logger import logger

log = logger(__name__)


def refine_cpr_data(date, *, max_speed=DEFAULT_MAX_SPEED,
                    distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Refine a CPR file for the given date.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16:q:q

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
    if is_valid_iso8601_date(date):
        os.chdir(REFINED_DIR)
        tasks.convert_cpr_file(date)
        return tasks.clean_raw_positions_data(CPR, date, float(max_speed),
                                              float(distance_accuracy))
    else:
        log.error("The date is not valid: %s", date)
        return False


def refine_fr24_data(date, *, max_speed=DEFAULT_MAX_SPEED,
                     distance_accuracy=DEFAULT_DISTANCE_ACCURACY,
                     airports_filename=DEFAULT_AIRPORTS_FILENAME):
    """
    Refine FR24 ADS-B data for the given date.

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

    airports_filename: string
        The name of a file containing airport codes for IATA to ICAO conversion,
        default: airports.csv

    Returns
    -------
        True if succesful, False otherwise.

    """
    if is_valid_iso8601_date(date):
        os.chdir(REFINED_DIR)
        tasks.convert_fr24_date(date)

        # Note: these 3 tasks could run in parallel
        tasks.clean_raw_positions_data(FR24, date, float(max_speed),
                                       float(distance_accuracy))
        tasks.convert_airport_codes(date, airports_filename)
        return tasks.extract_fleet_date(date)

    else:
        log.error("The date is not valid: %s", date)
        return False


def merge_cpr_fr24_data(date, *, max_speed=DEFAULT_MAX_SPEED,
                        distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Match, merge and clean refined CPR and FR24 ADS-B data for the given date.

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

    Returns
    -------
        True if succesful, False otherwise.

    """
    if is_valid_iso8601_date(date):
        os.chdir(REFINED_DIR)
        tasks.match_cpr_adsb_trajectories_on(date)
        tasks.merge_cpr_adsb_trajectories_on(date)

        return tasks.clean_raw_positions_data(CPR_FR24, date, float(max_speed),
                                              float(distance_accuracy))
    else:
        log.error("The date is not valid: %s", date)
        return False


def merge_cpr_fr24_overnight_flights(date):
    """
    Match, merge and clean merged CPR and FR24 ADS-B data for the given date,
    with merged CPR and FR24 ADS-B data for the previous day.

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

    Returns
    -------
        True if succesful, False otherwise.

    """
    if is_valid_iso8601_date(date):
        os.chdir(REFINED_DIR)
        if tasks.match_previous_days_flights(date):
            if tasks.merge_previous_days_data(date):
                return tasks.clean_overnight_cpr_fr24_positions(date)
    else:
        log.error("The date is not valid: %s", date)

    return False


def merge_apds_data(from_date, to_date, date):
    """
    Run the merge apt trajectories algorithm.
    """
    if tasks.match_apds_trajectories_on_day(from_date, to_date, date):
        return tasks.merge_apds_trajectories_on_day(from_date, to_date, date)
    else:
        return False
