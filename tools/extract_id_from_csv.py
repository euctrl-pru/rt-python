#!/usr/bin/env python
#
# Copyright (c) 2017 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import sys
import bz2
import errno
import gzip
import csv
from timeit import default_timer as timer

"""
This file extracts the rows of a .csv file that have 'id' in the fierst field
and writes the output into a file called '<id>.csv'.
It assumes that the input file is sorted in 'id' order and that the first row
is the header.

The input file must be in csv format and may be compressed in bz2 or gzip format.
"""

if len(sys.argv) < 3:
    print('Usage: extract_id_from_csv.py <filename> <id>')
    sys.exit(errno.EINVAL)

filename = sys.argv[1]
id_2_find = sys.argv[2]

# assume input file is sorted
is_sorted = True

output_filename = id_2_find + '.csv'

time0 = timer()

rows = []

# Open the csv file and read the rows
try:
    # decompress bz2 and gzip files
    is_bz2 = (filename[-1] == '2')
    is_gzip = (filename[-1] == 'z')
    with bz2.open(filename, 'rt',  newline='') if (is_bz2) else \
        gzip.open(filename, 'rt',  newline='') if (is_gzip) else \
            open(filename, 'r') as file:
        reader = csv.reader(file)

        # read the first row as the header
        rows.append(next(reader))

        # flag to indicate that id_2_find has been found
        found_id = False

        # Read each row until all rows with id_2_find have been found
        for row in reader:
            if row[0] == id_2_find:
                rows.append(row)
                found_id = True
            # have all rows with id_2_find have been found?
            elif is_sorted and found_id:
                break

except EnvironmentError:
    print('could not read file:', filename)
    sys.exit(errno.ENOENT)

time1 = timer()

print('read csv_file time (secs)', (time1 - time0))

# Require more than just the header row
if len(rows) < 2:
    print(id_2_find + ' not found.')
else:
    print('Found', len(rows) - 1, 'entries for', id_2_find)
    # Output the rows
    try:
        with open(output_filename, 'w', newline='') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)
    except EnvironmentError:
        print('could not write file:', output_filename)
        sys.exit(errno.EACCES)

    print('written file:', output_filename)

time2 = timer()
print('extract_id_from_csv time (secs)', (time2 - time0))
