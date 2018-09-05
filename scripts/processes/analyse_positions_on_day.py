#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Analyse trajectory position data for a specific day.
"""

import sys
import errno

from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import CPR_FR24
from pru.trajectory_analysis import DEFAULT_ACROSS_TRACK_TOLERANCE, \
    DEFAULT_MOVING_MEDIAN_SAMPLES, DEFAULT_MOVING_AVERAGE_SAMPLES, \
    DEFAULT_SPEED_MAX_DURATION, MOVING_AVERAGE_SPEED
from apps.analyse_position_data import DEFAULT_LOGGING_COUNT
from scripts.tasks import analyse_positions_on_date
from pru.logger import logger

log = logger(__name__)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: analyse_positions_on_day.py <date>'
              ' [across_track_tolerance] [time analysis method]'
              ' [median_filter_samples] [average_filter_samples]'
              ' [speed_max_duration] [logging_msg_count]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)

    across_track_tolerance = DEFAULT_ACROSS_TRACK_TOLERANCE
    if len(sys.argv) >= 3:
        try:
            across_track_tolerance = float(sys.argv[2])
        except ValueError:
            log.error(f'invalid across_track_tolerance: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    time_method = MOVING_AVERAGE_SPEED
    if len(sys.argv) >= 4:
        time_method = sys.argv[3]

    N = DEFAULT_MOVING_MEDIAN_SAMPLES
    if len(sys.argv) >= 5:
        N = int(sys.argv[4])

    M = DEFAULT_MOVING_AVERAGE_SAMPLES
    if len(sys.argv) >= 6:
        M = int(sys.argv[5])

    max_duration = DEFAULT_SPEED_MAX_DURATION
    if len(sys.argv) >= 7:
        try:
            max_duration = float(sys.argv[6])
        except ValueError:
            log.error(f'invalid speed_max_duration: {sys.argv[6]}')
            sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 8:
        logging_msg_count = int(sys.argv[7])

    if not analyse_positions_on_date(date, CPR_FR24,
                                     distance_tolerance=across_track_tolerance,
                                     time_method=time_method,
                                     N=N, M=M,
                                     max_duration=max_duration,
                                     logging_msg_count=logging_msg_count):
        sys.exit(errno.EACCES)
