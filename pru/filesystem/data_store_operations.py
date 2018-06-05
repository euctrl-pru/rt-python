# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Provides operations on the managed data.

Data structure on the bucket and on the local drive is mirrored.  Data
types and locatins are prescribed.
"""

import datetime
import os
import os.path as path
from os import environ as env
from pathlib import Path
from bz2 import BZ2Compressor, BZ2Decompressor
from pru.filesystem.google_bucket import list_bucket_objects, \
    copy_from_bucket, copy_to_bucket
from pru.env.env_constants import DATA_HOME, UPLOAD_DIR, BACKUPS_DIR, NOTEBOOK_HOME
from pru.trajectory_fields import BZ2_FILE_EXTENSION, \
    has_bz2_extension, is_valid_iso8601_date, compact_date
from pru.trajectory_files import APDS, CPR, FR24, CPR_FR24, APDS_CPR_FR24, IDS, \
    FLEET_DATA, ERROR_METRICS, TRAJECTORIES, TRAJ_METRICS, REF_POSITIONS, \
    INTERSECTIONS, SECTOR, AIRPORT, USER
from pru.logger import logger

log = logger(__name__)

# Local Directories
REFINED = 'refined'
REFINED_DIR = '/'.join([DATA_HOME, REFINED])

MERGED = 'merged'
MERGED_DIR = '/'.join([DATA_HOME, MERGED])

ANALYSIS = 'analysis'
ANALYSIS_DIR = '/'.join([DATA_HOME, ANALYSIS])

FLEET_DATA_DIR = '/'.join([DATA_HOME, FLEET_DATA])

# Supported processed data types correspond to bucket root directories

SOURCES = 'sources'

SOURCES_CPR = '/'.join([SOURCES, CPR])
SOURCES_FR24 = '/'.join([SOURCES, FR24])
SOURCES_APDS = '/'.join([SOURCES, APDS])

DAILY = 'daily'
DAILY_CPR_FR24 = '_'.join([DAILY, CPR_FR24])

SOURCES_MERGED_DAILY_CPR_FR24 = '/'.join([SOURCES, MERGED, DAILY_CPR_FR24])
SOURCES_MERGED_DAILY_CPR_FR24_IDS = '/'.join([SOURCES_MERGED_DAILY_CPR_FR24, IDS])

OVERNIGHT = 'overnight'
OVERNIGHT_CPR_FR24 = '_'.join([OVERNIGHT, CPR_FR24])

SOURCES_MERGED_OVERNIGHT_CPR_FR24 = '/'.join([SOURCES, MERGED, OVERNIGHT_CPR_FR24])
SOURCES_MERGED_OVERNIGHT_CPR_FR24_IDS = '/'.join([SOURCES_MERGED_OVERNIGHT_CPR_FR24, IDS])

SOURCES_MERGED_APDS_CPR_FR24 = '/'.join([SOURCES, MERGED, APDS_CPR_FR24])
SOURCES_MERGED_APDS_CPR_FR24_IDS = '/'.join([SOURCES_MERGED_APDS_CPR_FR24, IDS])

PRODUCTS = 'products'

PRODUCTS_FLEET = '/'.join([PRODUCTS, FLEET_DATA])

PRODUCTS_ERROR_METRICS_CPR = '/'.join([PRODUCTS, ERROR_METRICS, CPR])
PRODUCTS_ERROR_METRICS_FR24 = '/'.join([PRODUCTS, ERROR_METRICS, FR24])
PRODUCTS_ERROR_METRICS_CPR_FR24 = '/'.join([PRODUCTS, ERROR_METRICS, CPR_FR24])
PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT = '/'.join([PRODUCTS, ERROR_METRICS, CPR_FR24, OVERNIGHT])

PRODUCTS_TRAJECTORIES_CPR = '/'.join([PRODUCTS, TRAJECTORIES, CPR])
PRODUCTS_TRAJECTORIES_FR24 = '/'.join([PRODUCTS, TRAJECTORIES, FR24])
PRODUCTS_TRAJECTORIES_CPR_FR24 = '/'.join([PRODUCTS, TRAJECTORIES, CPR_FR24])

PRODUCTS_TRAJ_METRICS_CPR = '/'.join([PRODUCTS, TRAJ_METRICS, CPR])
PRODUCTS_TRAJ_METRICS_FR24 = '/'.join([PRODUCTS, TRAJ_METRICS, FR24])
PRODUCTS_TRAJ_METRICS_CPR_FR24 = '/'.join([PRODUCTS, TRAJ_METRICS, CPR_FR24])

PRODUCTS_REF_POSITIONS_CPR = '/'.join([PRODUCTS, REF_POSITIONS, CPR])
PRODUCTS_REF_POSITIONS_FR24 = '/'.join([PRODUCTS, REF_POSITIONS, FR24])
PRODUCTS_REF_POSITIONS_CPR_FR24 = '/'.join([PRODUCTS, REF_POSITIONS, CPR_FR24])

PRODUCTS_INTERSECTIONS_SECTOR = '/'.join([PRODUCTS, INTERSECTIONS, SECTOR])
PRODUCTS_INTERSECTIONS_SECTOR_CPR = '/'.join([PRODUCTS_INTERSECTIONS_SECTOR, CPR])
PRODUCTS_INTERSECTIONS_SECTOR_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_SECTOR, FR24])
PRODUCTS_INTERSECTIONS_SECTOR_CPR_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_SECTOR, CPR_FR24])

PRODUCTS_INTERSECTIONS_AIRPORT = '/'.join([PRODUCTS, INTERSECTIONS, AIRPORT])
PRODUCTS_INTERSECTIONS_AIRPORT_CPR = '/'.join([PRODUCTS_INTERSECTIONS_AIRPORT, CPR])
PRODUCTS_INTERSECTIONS_AIRPORT_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_AIRPORT, FR24])
PRODUCTS_INTERSECTIONS_AIRPORT_CPR_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_AIRPORT, CPR_FR24])

PRODUCTS_INTERSECTIONS_USER = '/'.join([PRODUCTS, INTERSECTIONS, USER])
PRODUCTS_INTERSECTIONS_USER_CPR = '/'.join([PRODUCTS_INTERSECTIONS_USER, CPR])
PRODUCTS_INTERSECTIONS_USER_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_USER, FR24])
PRODUCTS_INTERSECTIONS_USER_CPR_FR24 = '/'.join([PRODUCTS_INTERSECTIONS_USER, CPR_FR24])

# Supported unprocessed data types
AIRPORTS = "airports"
STANDS = "stands"
AIRPORTS_STANDS = '/'.join([AIRPORTS, STANDS])
AIRSPACES = "airspaces"

# The set of valid data types
VALID_DATA_TYPES = {APDS, CPR, FR24, CPR_FR24, SOURCES_CPR, SOURCES_FR24, SOURCES_APDS,
                    PRODUCTS_ERROR_METRICS_CPR, PRODUCTS_ERROR_METRICS_FR24, PRODUCTS_FLEET,
                    SOURCES_MERGED_DAILY_CPR_FR24, SOURCES_MERGED_DAILY_CPR_FR24_IDS,
                    SOURCES_MERGED_OVERNIGHT_CPR_FR24, SOURCES_MERGED_OVERNIGHT_CPR_FR24_IDS,
                    SOURCES_MERGED_APDS_CPR_FR24, SOURCES_MERGED_APDS_CPR_FR24_IDS,
                    PRODUCTS_ERROR_METRICS_CPR_FR24, PRODUCTS_ERROR_METRICS_CPR_FR24_OVERNIGHT,
                    PRODUCTS_TRAJECTORIES_CPR, PRODUCTS_TRAJ_METRICS_CPR,
                    PRODUCTS_TRAJECTORIES_FR24, PRODUCTS_TRAJ_METRICS_FR24,
                    PRODUCTS_TRAJECTORIES_CPR_FR24, PRODUCTS_TRAJ_METRICS_CPR_FR24,
                    PRODUCTS_REF_POSITIONS_CPR, PRODUCTS_REF_POSITIONS_FR24,
                    PRODUCTS_REF_POSITIONS_CPR_FR24, PRODUCTS_INTERSECTIONS_SECTOR_CPR,
                    PRODUCTS_INTERSECTIONS_SECTOR_FR24, PRODUCTS_INTERSECTIONS_SECTOR_CPR_FR24,
                    PRODUCTS_INTERSECTIONS_AIRPORT_CPR, PRODUCTS_INTERSECTIONS_AIRPORT_FR24,
                    PRODUCTS_INTERSECTIONS_AIRPORT_CPR_FR24, PRODUCTS_INTERSECTIONS_USER_CPR,
                    PRODUCTS_INTERSECTIONS_USER_FR24, PRODUCTS_INTERSECTIONS_USER_CPR_FR24}


# Supported location types
LOCAL = "local"
BUCKET = "bucket"

# Supported backup types
BACKUP_REF = "REF"
BACKUP_GEO = "GEO"
BACKUP_NOTEBOOKS = "NB"
BACKUP_REFINED = "REFINED"
BACKUP_INTERSECTIONS = "INTERSECTIONS"

# The set of valid backup types

VALID_BACKUPS = {BACKUP_REF, BACKUP_GEO, BACKUP_NOTEBOOKS, BACKUP_REFINED,
                 BACKUP_INTERSECTIONS}


def compress(file_path):
    """
    Compress in place file.
    If the file does not exist we return False
    If the file already has a bz2 extension we don't
    compress it.

    returns a tuple of success and the path string describing the compressed
    file.

    Parameters
    ----------
    file_path a valid path to a file to be compressed.

    """
    if Path(file_path).exists():
        if not has_bz2_extension(file_path):
            compressed_path = file_path + BZ2_FILE_EXTENSION
            compressor = BZ2Compressor()
            with open(file_path, 'rb') as uncompressed:
                with open(compressed_path, 'wb') as compressed:
                    for bytes in iter(uncompressed.readline, b''):
                        compressed.write(compressor.compress(bytes))
                    compressed.write(compressor.flush())
            return (True, compressed_path)
        else:
            return (True, file_path)
    else:
        return (False, "File does not exist: " + file_path)


def uncompress(file_path):
    """
    Uncompress in place file.
    If the file does not exist we return False
    If the file does not have a bz2 extension we don't
    uncompress it.

    returns a tuple of success and the path string describing the uncompressed
    file.

    Parameters
    ----------
    file_path a valid path to a file to be uncompressed.

    """
    if Path(file_path).exists():
        if has_bz2_extension(file_path):
            uncompressed_path = file_path[:-4]
            uncompressor = BZ2Decompressor()
            with open(file_path, 'rb') as compressed:
                with open(uncompressed_path, 'wb') as uncompressed:
                    for bytes in iter(compressed.readline, b''):
                        uncompressed.write(uncompressor.decompress(bytes))
                return (True, uncompressed_path)
        else:
            return (True, file_path)
    else:
        return (False, "File does not exist: " + file_path)


def validate_data_type_and_date(data_type, date=None):
    """
    Unprocessed data items are identified by type and date.

    Returns a tuple with a valid flag and if in error an error message.

    Parameters
    ----------
    data_type the data type
    date optional a date to match the data
    """
    valid_type = VALID_DATA_TYPES.__contains__(data_type)
    if date:
        valid_date = is_valid_iso8601_date(date)
    else:
        valid_date = True
    if valid_type and valid_date:
        return True, None
    else:
        return False, "Validation failure, data_type: " + str(valid_type) + \
            " date: " + str(valid_date)


def filter_date(names, date, data_type=None):
    """
    Given a list of file names filter out those that do not contain
    the given date.

    Parameters
    ----------
    names a list of file names
    date the iso format date
    data_type is used to process the odd filenames of unprocessed cpr files.
    """
    compacted_date = date
    if names:
        if data_type == CPR:
            compacted_date = compact_date(date)
        return [name for name in names if compacted_date in name]
    else:
        return []


def get_unprocessed(data_type, data_date, local_path_string=UPLOAD_DIR):
    """
    Gets data from the bucket.
    The destination is assuemd to be local.
    If no date is given all the dates for the specified data type are copied.

    Parameters
    ----------
    data_type describes the type of unprocessed data
    data_date the date we are interested in
    local_path_string is defaulted to the local upload dir
    """
    log.debug("Getting data item from bucket with type: " + str(data_type))
    valid, error_message = validate_data_type_and_date(data_type, data_date)
    if valid:
        _, tail = path.split(UPLOAD_DIR)
        source_path = tail + '/' + data_type
        destination_path = local_path_string + "/" + data_type
        log.debug("Source path: " + source_path + " destnation path: " + destination_path)
        objects = list_bucket_objects(source_path)
        names = [obj.name for obj in objects]
        log.debug("Found names: " + str(names))
        # Only include the date specified
        if data_date is not None:
            names = filter_date(names, data_date, data_type)
        log.debug("Getting unprocessed data with names: " + str(names))
        # Remove any directory strings
        filtered_objects = [obj for obj in objects if names.__contains__(
            obj.name) and not obj.name.endswith('/')]
        log.debug("Getting unprocessed filtered data: " + str(filtered_objects))
        copy_from_bucket(filtered_objects, destination_path)

    else:
        return error_message


def get_airspaces(airspaces_file_name, local_path_string=DATA_HOME):
    """
    Gets the airspaces descriptions required to support data processing.
    The data source location and file name is fixed.

    Parameters
    ----------
    local_path_string is defaulted to the known local airspaces data location.
    """
    destination_path = '/'.join([local_path_string, AIRSPACES])
    objects = list_bucket_objects(AIRSPACES)
    filtered_objects = [obj for obj in objects if airspaces_file_name in obj.name]
    log.debug("Getting airspaces file: " + str(filtered_objects) + " to: " +
              destination_path)
    copy_from_bucket(filtered_objects, destination_path)
    return destination_path


def get_user_airspaces(user_airspaces_file_name, local_path_string=DATA_HOME):
    """
    Gets the user airspaces descriptions required to support data processing.
    The data source location and file name is fixed.

    Parameters
    ----------
    local_path_string is defaulted to the known local user airspaces data location.
    """
    destination_path = '/'.join([local_path_string, AIRSPACES])
    objects = list_bucket_objects(AIRSPACES)
    filtered_objects = [obj for obj in objects if user_airspaces_file_name in obj.name]
    log.debug("Getting user airspaces file: " + str(filtered_objects) + " to: " +
              destination_path)
    copy_from_bucket(filtered_objects, destination_path)
    return destination_path


def get_airports(airports_file_name, local_path_string=DATA_HOME):
    """
    Gets the airports descriptions required to support data processing.
    The data source location and file name is fixed.

    Parameters
    ----------
    local_path_string is defaulted to the known local airport data location.
    """
    destination_path = '/'.join([local_path_string, AIRPORTS])
    objects = list_bucket_objects(AIRPORTS)
    filtered_objects = [obj for obj in objects if airports_file_name in obj.name]
    log.debug("Getting airports file: " + str(filtered_objects) + " to: " +
              destination_path)
    copy_from_bucket(filtered_objects, destination_path)
    return destination_path


def get_stands(stands_file_name, local_path_string=DATA_HOME):
    """
    Gets the stands descriptions required to support data processing.
    The data source name is fixed.

    Parameters
    ----------
    local_path_string is defaulted to the known local airport data location.
    """
    destination_path = '/'.join([local_path_string, AIRPORTS_STANDS])
    objects = list_bucket_objects(AIRPORTS_STANDS)
    filtered_objects = [obj for obj in objects if stands_file_name in obj.name]
    log.debug("Getting stands file: " + str(filtered_objects) + " to: " +
              destination_path)
    copy_from_bucket(filtered_objects, destination_path)
    return destination_path


def get_apds(apds_filename, local_path_string=UPLOAD_DIR):
    """
    Gets the apds descriptions required to support data processing.

    Parameters
    ----------
    apds_filename The file name
    """
    log.debug("Getting apds file: %s", apds_filename)
    destination_path = local_path_string + "/" + APDS
    _, tail = path.split(UPLOAD_DIR)
    source_path = tail + '/' + APDS
    objects = list_bucket_objects(source_path)
    filtered_objects = [obj for obj in objects if apds_filename in obj.name]
    log.debug("Getting apds file: " + str(filtered_objects) + " to: " +
              destination_path)
    copy_from_bucket(filtered_objects, destination_path)
    return destination_path


def put_processed(data_type, local_path_strings):
    """
    Put processed data items from a list into the bucket.  These are always
    compressed.  If compression fails for any reason we dont write, function
    returns False, else we return True.

    Parameters
    ----------
    data_type the type of data to put.  This is prescribed for each data type.
    local_path_strings is a list of paths to the files to upload.
    """
    log.info('Putting data items: %s to bucket: %s',
             str(local_path_strings), data_type)
    # Check the data class is understood
    valid, error_messag = validate_data_type_and_date(data_type)
    if valid:
        # Compress the files in place
        compress_result = [compress(file_path) for file_path in local_path_strings]
        success, compressed_file_paths = map(list, zip(*compress_result))
        # Only proceed if all the files were sucuessfully compressed
        if (all(success)):
            log.debug("Compressed the files: " + str(local_path_strings))
            destinations = [data_type + "/" + path.split(source)[1]
                            for source in compressed_file_paths]
            log.debug("Calling low level copy to bucket")
            copy_to_bucket(compressed_file_paths, destinations)
            log.debug("Removing compressed files : %s", str(compressed_file_paths))
            [os.remove(file_path) for file_path in compressed_file_paths]
            return True
        else:
            log.error("Failed to compress one or more of the files, result: " +
                      str(compress_result))
            return False
    else:
        log.error("Invalid data type: " + data_type)
        return False


def get_processed(data_type, filenames, local_directory='.'):
    """
    Get processed data items from the bucket of the given type and name to a
    local path.  These are always compressed in the bucket we decompress them
    on read.  If decompression fails for any reason we fail the copy and the
    function returns false otherwise true.

    Parameters
    ----------
    data_type the type of data to get.  This is prescribed for each data type.
    filenames a list of file names
    local_directory is the path to copy the file to and must exist.
    """
    log.info('Getting data items: %s from bucket: %s to: %s',
             str(filenames), data_type, local_directory)
    valid, error_messag = validate_data_type_and_date(data_type)
    existing_path = path_exists(local_directory)
    if valid and existing_path:
        log.debug("Getting files %s", str(filenames))
        paths = [data_type + "/" + filename + ".bz2" for filename in filenames]
        log.debug("paths : %s", str(paths))
        # Note here objects_list is a list of lists
        objects_list = [list_bucket_objects(path) for path in paths]
        [copy_from_bucket(objects, local_directory) for objects in objects_list]
        log.debug("Uncompressing files %s", str(filenames))
        uncompress_result = [uncompress(local_directory + "/" + filename + ".bz2")
                             for filename in filenames]
        success, uncompressed_file_paths = map(list, zip(*uncompress_result))
        if success:
            # delete the compressed processed files
            compressed_file_paths = [filename + ".bz2" for filename in filenames]
            [os.remove(file_path) for file_path in compressed_file_paths]
        return success
    else:
        log.error("Either the data type was invalid or the path does not exist")
        return False


def bucket_path_exists(path_string):
    """
    Find out if a bucket path is present.  To do this, list the conents of
    the root path and check for existence.
    """
    log.debug("Checking for the existance of path: " + path_string)
    objects = list_bucket_objects("")
    return (set([obj.name for obj in objects])).__contains__(path_string)


def path_exists(path_string, location=LOCAL):
    """
    Find out if a path exists, works for dir paths and dir_path/file
    """
    if location == LOCAL:
        return Path(path_string).exists()
    else:
        return bucket_path_exists(path_string)


def file_exists(path_string, file_name, location=LOCAL):
    """
    Check if the given file is present on the given path at the given location.
    """
    if location == LOCAL:
        return path_exists(path_string) and Path(path_string).contains(file_name)
    else:
        return bucket_path_exists(path + "/" + file_name)


def list_bucket(path_string):
    """
    List data items in the bucket.
    """
    objects = list_bucket_objects(path_string)
    return [obj.name for obj in objects]


def list_local(path_string):
    """
    List data items in the local data structure.
    """
    return [str(s) for s in Path(path_string).glob("*")]


def list_path(path_string, location=LOCAL):
    """
    List the conents of a path.  Includes sub paths but does not recurse.
    """
    if location is LOCAL:
        if path_exists(path_string):
            return list_local(path_string)
        else:
            return []
    else:
        return list_bucket(path_string)


def transform_iso_datetime(iso_datetime):
    """
    iso date times are of the form 2018-03-22T11:12:14, this is not a valid
    file system name and oses (osx for example,) transform the ':' into '/'
    which is not what we want in our bucket object names.

    We transfor the ':' into a '-' so that the iso datetime becomes
    2018-03-22T11-12-14.
    """
    return iso_datetime.replace(':', '-')


def backup(backup_types):
    """
    Backs up the given types.  Data is copied to the backups directory under
    the user name and current date time.

    Parameters
    ----------
    types - a list of backup types

    eg - backup([BACKUP_NOTEBOOKS])

    """
    # Make sure the backup type is specified.
    valid = [(VALID_BACKUPS.__contains__(backup_type), backup_type) for backup_type in backup_types]
    # Temp check here, we only support notebooks
    if all(valid) and backup_types[0] == BACKUP_NOTEBOOKS:
        # We only support NB backups at the moment
        log.debug("backing up data for types: " + str(backup_types))
        date_string = transform_iso_datetime(
            datetime.datetime.today().isoformat(timespec='seconds'))
        backup_base = path.split(BACKUPS_DIR)[1]
        nb_path = backup_base + '/' + env['JUPYTERHUB_USER'] + '/' + date_string + '/notebooks'
        log.info("Backing up notebooks from: " + NOTEBOOK_HOME + " to " + nb_path)
        notebooks = [str(s) for s in Path(NOTEBOOK_HOME).glob("*.ipynb")]
        nb_paths = [nb_path + '/' + path.split(notebook)[1] for notebook in notebooks]
        copy_to_bucket(notebooks, nb_paths)
        return True
    else:
        log.error("There was a problem with one of the backup types: " +
                  str(valid))
        return False
