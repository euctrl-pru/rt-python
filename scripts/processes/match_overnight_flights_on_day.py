#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Matches merged CPR and FR24 flights for the given day with merged CPR and FR24
flights for the previous day.
"""

import sys
import errno
import gc

from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import create_match_overnight_flights_input_filenames, \
    PREV_DAY, create_matching_ids_filename, \
    create_extract_overnight_data_input_filenames, \
    create_extract_overnight_data_output_filenames

from pru.filesystem.data_store_operations import get_processed, put_processed, \
    REFINED_MERGED_DAILY_CPR_FR24, REFINED_MERGED_OVERNIGHT_CPR_FR24, \
    REFINED_MERGED_OVERNIGHT_CPR_FR24_IDS

from apps.match_overnight_flights import match_overnight_flights, \
    DEFAULT_MAXIMUM_TIME_DELTA
from apps.extract_overnight_data import extract_overnight_data

from pru.logger import logger

log = logger(__name__)


def match_overnight_flights_on_day(date,
                                   max_time_difference=DEFAULT_MAXIMUM_TIME_DELTA):
    """
    Match flights for the given day with flights for the previous day.

    Parameters
    ----------
    date: string
        The date in ISO8601 format, e.g. 2017-08-16

    """
    if is_valid_iso8601_date(date):

        # get the CPR data from the Google bucket
        log.info(f'Getting data for date: {date}')

        match_flights_files = create_match_overnight_flights_input_filenames(date)
        if not get_processed(REFINED_MERGED_DAILY_CPR_FR24, match_flights_files):
            log.error('Flights file not found in daily_cpr_fr24 bucket')
            return errno.ENOENT

        error_code = match_overnight_flights(match_flights_files, max_time_difference)
        if error_code:
            return error_code
        gc.collect()

        prev_ids_filename = create_matching_ids_filename(PREV_DAY, date)
        if not put_processed(REFINED_MERGED_OVERNIGHT_CPR_FR24_IDS, [prev_ids_filename]):
            log.error('Could not write ids to overnight_cpr_fr24/ids bucket')
            return errno.EACCES

        extract_data_input_files = create_extract_overnight_data_input_filenames(date)
        if not get_processed(REFINED_MERGED_DAILY_CPR_FR24, extract_data_input_files[2:]):
            log.error('Positions or events file not found in daily_cpr_fr24 bucket')
            return errno.ENOENT

        error_code = extract_overnight_data(extract_data_input_files)
        if error_code:
            return error_code

        extract_data_output_files = create_extract_overnight_data_output_filenames(date)
        if not put_processed(REFINED_MERGED_OVERNIGHT_CPR_FR24, extract_data_output_files):
            log.error('Could not write to overnight_cpr_fr24 bucket')
            return errno.EACCES

    else:
        log.error(f'invalid date: {date}')
        return errno.EINVAL

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: match_overnight_flights_on_day.py <date>'
              '[maximum time difference]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)

    max_time_difference = DEFAULT_MAXIMUM_TIME_DELTA
    if len(sys.argv) >= 3:
        try:
            max_time_difference = float(sys.argv[2])
        except ValueError:
            log.error(f'invalid max_time_difference: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    error_code = match_overnight_flights_on_day(date, max_time_difference)
    if error_code:
        sys.exit(error_code)
