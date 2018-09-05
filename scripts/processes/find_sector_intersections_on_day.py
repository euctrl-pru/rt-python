#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Find trajectory airspace sector intersections for the given date.
"""

import sys
import errno

from pru.trajectory_fields import is_valid_iso8601_date
from pru.trajectory_files import CPR_FR24, create_trajectories_filename
from apps.find_sector_intersections import DEFAULT_LOGGING_COUNT
from scripts.tasks import find_trajectory_sector_intersections
from pru.logger import logger

log = logger(__name__)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_sector_intersections_on_day.py <date>'
              ' [logging_msg_count]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    trajectory_filename = 'mas_05_'
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)
    else:
        trajectory_filename += create_trajectories_filename(CPR_FR24, date)

    logging_msg_count = DEFAULT_LOGGING_COUNT
    if len(sys.argv) >= 3:
        logging_msg_count = int(sys.argv[2])

    if not find_trajectory_sector_intersections(trajectory_filename, CPR_FR24,
                                                logging_msg_count):
        sys.exit(errno.EACCES)
