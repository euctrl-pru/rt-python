#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import sys
import errno
import gzip
import csv
from timeit import default_timer as timer

"""
This file extracts the rows of a CPR file that have an 'id' that matches
one of the ids in the ids_filename.

The CPR input file must be in a valid format and may be compressed in gzip format.
"""

if len(sys.argv) < 3:
    print('Usage: extract_ids_from_cpr_file.py <filename> <ids_filename>')
    sys.exit(errno.EINVAL)

filename = sys.argv[1]
ids_filename = sys.argv[2]

ids = set()

# Open the ids_filename file and read the rows
try:
    # decompress bz2 and gzip files
    with open(ids_filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # skip the first row as the header
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
    # decompress bz2 and gzip files
    is_gzip = (filename[-1] == 'z')

    # remove the extension from the output filename
    if is_gzip:
        output_filename = output_filename[:-len('.gz')]

    with gzip.open(filename, 'rt',  newline='') if (is_gzip) else \
            open(filename, 'r') as file:
        reader = csv.reader(file, delimiter=';')

        # Read each row until all rows with id_2_find have been found
        for row in reader:
            id = row[1]  # TACT_ID is row 1
            if id in ids:
                rows.append(row)

except EnvironmentError:
    print('could not read file:', filename)
    sys.exit(errno.ENOENT)

time1 = timer()

print('read csv_file time (secs)', (time1 - time0))

# Require more than just one row
if len(rows) < 1:
    print(ids_filename + ' not found.')
else:
    print('Found', len(rows) - 1, 'entries for', ids_filename)
    # Output the rows
    try:
        with open(output_filename, 'w', newline='') as file:
            writer = csv.writer(file, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)
    except EnvironmentError:
        print('could not write file:', output_filename)
        sys.exit(errno.EACCES)

    print('written file:', output_filename)

time2 = timer()
print('extract_ids_from_cpr_file time (secs)', (time2 - time0))
