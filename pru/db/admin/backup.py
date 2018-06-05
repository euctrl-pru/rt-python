#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
#
"""
Provides database backup and restore operations for use by a db admin notebook.
"""
from sh import pg_dump, psql
from pru.filesystem.google_bucket import copy_to_bucket, copy_from_bucket, list_bucket_objects
from pru.filesystem.data_store_operations import compress, uncompress
import pru.db.context as ctx
from os import environ as env
from datetime import datetime

LOCAL_REF_FILE_NAME = 'reference_backup.sql'
LOCAL_AIRSPACE_FILE_NAME = 'airspace_backup.sql'


def _make_remote_bucket_path(file_name, date_time):
    """
    Make a bucket path for a file that is in the bucket.
    """
    user = env.get('JUPYTERHUB_USER')
    return '/'.join(['backups', user, 'databases', date_time, file_name])


def _handle_copy_up(file_name):
    """
    Copy the backup file to the bucket.
    """
    compress(file_name)
    now = datetime.today()
    date_time = now.isoformat(timespec='seconds')
    bucket_path = _make_remote_bucket_path(file_name + '.bz2', date_time)
    copy_to_bucket([file_name + '.bz2'], [bucket_path])
    return bucket_path


def _handle_copy_down(file_name, date_time):
    """
    Copy the backup file from the bucket.
    """
    remote_bucket_path = _make_remote_bucket_path(file_name + '.bz2', date_time)
    bucket_objects = list_bucket_objects(remote_bucket_path)
    copy_from_bucket(bucket_objects, '.')
    uncompress(file_name + '.bz2')


def backup_reference():
    """
    Dump the reference db to sql.
    """
    with open(LOCAL_REF_FILE_NAME, 'wb') as f:
        pg_dump('-h', ctx.ref_db_hostname, '-U', 'postgres', '-d', ctx.CONTEXT[ctx.DB_NAME], _out=f)
    return _handle_copy_up(LOCAL_REF_FILE_NAME)


def backup_airspace():
    """
    Dump the airspace db to sql.
    """
    with open(LOCAL_AIRSPACE_FILE_NAME, 'wb') as f:
        pg_dump('-h', ctx.geo_db_hostname, '-U', 'postgres', '-d', ctx.CONTEXT[ctx.DB_NAME], _out=f)
    return _handle_copy_up(LOCAL_AIRSPACE_FILE_NAME)


def restore_reference(date_time):
    """
    Restore the reference db.
    """
    _handle_copy_down(LOCAL_REF_FILE_NAME, date_time)
    psql('-h', ctx.ref_db_hostname, '-U', 'postgres', '-f', LOCAL_REF_FILE_NAME, ctx.CONTEXT[ctx.DB_NAME])


def restore_airspace(date_time):
    """
    Restore the airspace db.
    """
    _handle_copy_down(LOCAL_AIRSPACE_FILE_NAME, date_time)
    psql('-h', ctx.geo_db_hostname, '-U', 'postgres', '-f', LOCAL_AIRSPACE_FILE_NAME, ctx.CONTEXT[ctx.DB_NAME])
