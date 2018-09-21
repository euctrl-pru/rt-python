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

from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import create_merge_overnight_flight_data_input_filenames, \
    create_merge_overnight_flight_data_output_filenames, \
    create_clean_position_data_filenames, CPR_FR24

from pru.filesystem.data_store_operations import get_processed, put_processed, \
    REFINED_MERGED_OVERNIGHT_CPR_FR24, PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT

from apps.merge_overnight_flight_data import merge_overnight_flight_data
from pru.trajectory_cleaning import DEFAULT_MAX_SPEED, DEFAULT_DISTANCE_ACCURACY
from apps.clean_position_data import clean_position_data

from pru.logger import logger

log = logger(__name__)


def merge_overnight_data_on_day(date, max_speed=DEFAULT_MAX_SPEED,
                                distance_accuracy=DEFAULT_DISTANCE_ACCURACY):
    """
    Match flights for the given day with flights for the previous day.

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

        # get the CPR data from the Google bucket
        log.info(f'Getting data for date: {date}')

        merge_files = create_merge_overnight_flight_data_input_filenames(date)
        if not get_processed(REFINED_MERGED_OVERNIGHT_CPR_FR24, merge_files):
            log.error('Flights file not found in overnight_cpr_fr24 bucket')
            return errno.ENOENT

        error_code = merge_overnight_flight_data(merge_files)
        if error_code:
            return error_code

        output_files = create_merge_overnight_flight_data_output_filenames(date)
        if not put_processed(REFINED_MERGED_OVERNIGHT_CPR_FR24, output_files):
            log.error('Could not merged files to overnight_cpr_fr24 bucket')
            return errno.EACCES

        raw_filename = output_files[1]
        error_code = clean_position_data(raw_filename, max_speed, distance_accuracy)
        if error_code:
            log.error('clean_position_data error file: {raw_filename}')
            return error_code

        filenames = create_clean_position_data_filenames(CPR_FR24, date)

        source_path = REFINED_MERGED_OVERNIGHT_CPR_FR24
        if not put_processed(source_path, filenames[:1]):
            log.error('Could not write file: {filenames[:1]} to bucket')
            return errno.EACCES

        errors_path = PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT
        if not put_processed(errors_path, filenames[1:]):
            log.error('Could not write file: {filenames[1:]} to bucket')
            return errno.EACCES

    else:
        log.error(f'invalid date: {date}')
        return errno.EINVAL

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: merge_overnight_data_on_day.py <date>'
              ' [max_speed] [distance_accuracy]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)

    max_speed = DEFAULT_MAX_SPEED
    if len(sys.argv) >= 3:
        max_speed = float(sys.argv[2])

    distance_accuracy = DEFAULT_DISTANCE_ACCURACY
    if len(sys.argv) >= 4:
        distance_accuracy = float(sys.argv[3])

    error_code = merge_overnight_data_on_day(date, max_speed, distance_accuracy)
    if error_code:
        sys.exit(error_code)
