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
from pru.trajectory_airport_intersections import DEFAULT_RADIUS
from apps.find_airport_intersections import DEFAULT_MOVEMENTS_AIRPORTS_FILENAME
from scripts.tasks import find_trajectory_airport_intersections
from pru.logger import logger

log = logger(__name__)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: find_airport_intersections_on_day.py <date>'
              ' [radius] [airports_filename]')
        sys.exit(errno.EINVAL)

    date = sys.argv[1]
    trajectory_filename = 'mas_05_'
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)
    else:
        trajectory_filename += create_trajectories_filename(CPR_FR24, date)

    radius = DEFAULT_RADIUS
    if len(sys.argv) >= 3:
        try:
            radius = float(sys.argv[2])
        except ValueError:
            log.error(f'invalid radius: {sys.argv[2]}')
            sys.exit(errno.EINVAL)

    airports_filename = DEFAULT_MOVEMENTS_AIRPORTS_FILENAME
    if len(sys.argv) >= 4:
        airports_filename = sys.argv[3]

    if not find_trajectory_airport_intersections(trajectory_filename, CPR_FR24,
                                                 radius, airports_filename):
        sys.exit(errno.EACCES)
