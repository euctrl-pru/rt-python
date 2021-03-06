#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import sys
import bz2
import errno
import csv
from timeit import default_timer as timer

"""
This file extracts the rows of an FR24 .csv file that have an 'id' that matches
one of the ids in the ids_filename.

The FR24 input file must be in csv format and may be compressed in bz2 format.
"""

if len(sys.argv) < 3:
    print('Usage: extract_ids_from_fr24_csv.py <filename> <ids_filename>')
    sys.exit(errno.EINVAL)

filename = sys.argv[1]
ids_filename = sys.argv[2]

# An empty set of ids
ids = set()

# Open the ids_filename file and read the rows
try:
    with open(ids_filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # skip the first row as a header
        for row in reader:  # add the first item in every row as the ids
            ids.add(row[0])

except EnvironmentError:
    print('could not read file:', ids_filename)
    sys.exit(errno.ENOENT)

output_filename = 'ids_' + filename

time0 = timer()

rows = []

# Open the csv file and read the rows
try:
    # decompress bz2 files
    is_bz2 = (filename[-1] == '2')

    # remove the extension from the output filename
    if is_bz2:
        output_filename = output_filename[:-len('.bz2')]

    with bz2.open(filename, 'rt',  newline='') if (is_bz2) else \
            open(filename, 'r') as file:
        reader = csv.reader(file)

        # read the first row as the header
        rows.append(next(reader))

        # Read each row until all rows with id_2_find have been found
        for row in reader:
            # Note: ids have 0x prepended to them
            id = '0x' + row[0]
            if id in ids:
                rows.append(row)

except EnvironmentError:
    print('could not read file:', filename)
    sys.exit(errno.ENOENT)

time1 = timer()

print('read csv_file time (secs)', (time1 - time0))

# Require more than just the header row
if len(rows) < 2:
    print(ids_filename + ' not found.')
else:
    print('Found', len(rows) - 1, 'entries for', ids_filename)
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
print('extract_ids_from_fr24_csv time (secs)', (time2 - time0))
