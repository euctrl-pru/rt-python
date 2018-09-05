#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Interpolate trajectories for the given date.
"""

import sys
import errno

from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import CPR_FR24, create_trajectories_filename
from pru.trajectory_interpolation import DEFAULT_STRAIGHT_INTERVAL, \
    DEFAULT_TURN_INTERVAL
from apps.interpolate_trajectories import DEFAULT_LOGGING_COUNT
from scripts.tasks import interpolate_trajectory_file
from pru.logger import logger

log = logger(__name__)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: interpolate_trajectory_on_day.py <date>'
              ' [straight_interval] [turn_interval] [logging_msg_count]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    trajectory_filename = 'mas_05_'
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)
    else:
        trajectory_filename += create_trajectories_filename(CPR_FR24, date)

    straight_interval = DEFAULT_STRAIGHT_INTERVAL
    if len(sys.argv) >= 3:
        try:
            straight_interval = float(sys.argv[2])
        except ValueError:
            log.error('invalid straight_interval: %s', sys.argv[2])
            sys.exit(errno.EINVAL)

    turn_interval = DEFAULT_TURN_INTERVAL
    if len(sys.argv) >= 4:
        try:
            turn_interval = float(sys.argv[3])
        except ValueError:
            log.error('invalid turn_interval: %s', sys.argv[3])
            sys.exit(errno.EINVAL)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 5:
        logging_msg_count = int(sys.argv[4])

    if not interpolate_trajectory_file(trajectory_filename, CPR_FR24,
                                       straight_interval, turn_interval,
                                       logging_msg_count):
        sys.exit(errno.EACCES)
