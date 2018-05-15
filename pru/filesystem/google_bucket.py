# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

""" Low level operations on Google bucket store.  """

import os.path as path
from libcloud.storage.drivers.google_storage import GoogleStorageDriver
from pru.env.env_constants import COMPUTE_ENGINE_SERVICE_ACCOUNT, PEM_FILE
from pru.env.env_constants import PROJECT_NAME, BUCKET_NAME
import pru.logger as logger


log = logger.logger(__name__)


def _get_driver():
    return GoogleStorageDriver(key=COMPUTE_ENGINE_SERVICE_ACCOUNT,
                               secret=PEM_FILE,
                               project=PROJECT_NAME)


def _get_bucket(driver):
    return driver.get_container(BUCKET_NAME)


def list_bucket_objects(path_string):
    """
    This returns a list of objects not names.  The list will include
    any paths that are not present as file objects.

    Parameters
    ----------
    path_string a string from the top of the bucket as a base to list objects.

    """
    log.debug("Listing objects in bucket path: " + path_string)
    driver = _get_driver()
    container = _get_bucket(driver)
    objects = driver.list_container_objects(container, ex_prefix=path_string)
    log.debug("Found the following in path: " + path_string + " " + str(objects))
    return objects


def copy_from_bucket(remote_objects, local_path, overwrite=True):
    """
    Copies files from the bucket at the given path to the given directory.

    Parameters
    ----------
    remote_objects A list of objects as returned by list_bucket_objects.
    local_path a valid file system path
    """
    driver = _get_driver()
    bucket = _get_bucket(driver)
    log.debug("Copying objects : \n" +
              str([obj.name for obj in remote_objects]) + "from container  " +
              bucket.name +
              "\n to path : " + local_path)
    for obj in remote_objects:
        obj = driver.get_object(container_name=bucket.name,
                                object_name=obj.name)
        filename = path.basename(obj.name)
        obj.download(destination_path=local_path + '/' + filename,
                     overwrite_existing=overwrite)


def copy_to_bucket(local_paths, remote_paths, overwrite=True):
    """
    Parameters
    ----------
    local_paths a list of valid file system paths that each identify an object
                to upload
    remote_paths a list of valid remote bucket paths that each identify a
                 target object path.
    """
    driver = _get_driver()
    bucket = _get_bucket(driver)
    log.debug("Copying objects from paths : \n" + str(local_paths) +
              "\n to bucket at " + str(remote_paths))
    for source, destination in zip(local_paths, remote_paths):
        driver.upload_object(source, bucket, destination, verify_hash=False)
