#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Matches and merges APDS data (over the gven date range) with merged CPR and
FR24 data for a given day.
"""

import sys
import errno

from pru.trajectory_fields import is_valid_iso8601_date
from scripts.tasks import \
    match_apds_trajectories_on_day, merge_apds_trajectories_on_day
from pru.logger import logger

log = logger(__name__)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: merge_apds_data_on_day.py <from_date> <to_date> <date>')
        sys.exit(errno.EINVAL)

    from_date = sys.argv[1]
    if not is_valid_iso8601_date(from_date):
        log.error(f'invalid from_date: {from_date}')
        sys.exit(errno.EINVAL)

    to_date = sys.argv[2]
    if not is_valid_iso8601_date(to_date):
        log.error(f'invalid to_date: {to_date}')
        sys.exit(errno.EINVAL)

    date = sys.argv[3]
    if not is_valid_iso8601_date(date):
        log.error(f'invalid date: {date}')
        sys.exit(errno.EINVAL)

    if not match_apds_trajectories_on_day(from_date, to_date, date):
        sys.exit(errno.EACCES)

    if not merge_apds_trajectories_on_day(from_date, to_date, date):
        sys.exit(errno.EACCES)
