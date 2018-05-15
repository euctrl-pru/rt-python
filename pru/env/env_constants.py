# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

# These names represent environment var names.  The environment is normally
# configured by either the docker image build, the docker image run or the
# Kubernetes image yaml configuration file.

"""
    Environmental constants.  Provides a layer over the environment vars.
    The reload function allows these vars to be updated as would be required
    in unit testing.
"""

from os import environ as env

# These represent the names of env vars that configure the project
PROJECT_NAME_ENV = "PROJECT_NAME"
BUCKET_NAME_ENV = "BUCKET_NAME"
PROJECT_HOME_ENV = "PROJECT_HOME"    # The source code directory
PRU_HOME_ENV = "PRU_HOME"            # The PRU configuration directory
DATA_HOME_ENV = "DATA_HOME"          # The base of the data directory
SHARED_HOME_ENV = "SHARED_HOME"      # Shared data area for all users
LOGGER_HOME_ENV = 'LOGGER_HOME'      # Log files and configuration
NOTEBOOK_HOME_ENV = 'NOTEBOOK_HOME'  # Base directory for notebooks


# Working data directory env var names
AIRPORTS_ENV = "AIRPORTS"
AIRSPACES_ENV = "AIRSPACES"
BACKUPS_ENV = "BACKUPS"
BUSINESS_LOGS_ENV = "BUSINESS_LOGS"
UPLOAD_ENV = "UPLOAD_DIR"

# JupyterHub specific env var names
JUPYTERHUB_USER_ENV = "JUPYTERHUB_USER"

PYTHONPATH_ENV = "PYTHONPATH"

MESSAGE_SERVER_PORT_ENV = "MESSAGE_SERVER_PORT"
MESSAGE_SERVER_HOST_ENV = "MESSAGE_SERVER_HOST"
MESSAGE_SERVER_USER_ENV = "MESSAGE_SERVER_USER"
MESSAGE_SERVER_PASSWORD_ENV = "MESSAGE_SERVER_PASSWORD"

# Cluster envs
COMPUTE_ENGINE_SERVICE_ACCOUNT_ENV = "COMPUTE_ENGINE_SERVICE_ACCOUNT"
PEM_FILE_ENV = "PEM_FILE"

# Environmental values read in.  Some may be None if the values are not present
# on a specific container.

# Project configuration
PROJECT_NAME = env.get(PROJECT_NAME_ENV)
BUCKET_NAME = env.get(BUCKET_NAME_ENV)
PROJECT_HOME = env.get(PROJECT_HOME_ENV)
PRU_HOME = env.get(PRU_HOME_ENV)
DATA_HOME = env.get(DATA_HOME_ENV)
SHARED_HOME = env.get(SHARED_HOME_ENV)
LOGGER_HOME = env.get(LOGGER_HOME_ENV)
NOTEBOOK_HOME = env.get(NOTEBOOK_HOME_ENV)


# Data related
AIRPORTS_DIR = env.get(AIRPORTS_ENV)
AIRSPACES_DIR = env.get(AIRSPACES_ENV)
BACKUPS_DIR = env.get(BACKUPS_ENV)
BUSINESS_LOGS_DIR = env.get(BUSINESS_LOGS_ENV)
UPLOAD_DIR = env.get(UPLOAD_ENV)

# Jupyterhub specific values
JUPYTERHUB_USER = env.get(JUPYTERHUB_USER_ENV)

PYTHONPATH = env.get(PYTHONPATH_ENV)

MESSAGE_SERVER_PORT = env.get(MESSAGE_SERVER_PORT_ENV)
MESSAGE_SERVER_HOST = env.get(MESSAGE_SERVER_HOST_ENV)
MESSAGE_SERVER_USER = env.get(MESSAGE_SERVER_USER_ENV)
MESSAGE_SERVER_PASSWORD = env.get(MESSAGE_SERVER_PASSWORD_ENV)

# Cluster envs
COMPUTE_ENGINE_SERVICE_ACCOUNT = env.get(COMPUTE_ENGINE_SERVICE_ACCOUNT_ENV)
PEM_FILE = env.get(PEM_FILE_ENV)


def reload():
    """
        Reload the above - may be used in testing
    """
    # Project configuration
    global PROJECT_NAME, BUCKET_NAME, PROJECT_HOME, PRU_HOME, DATA_HOME
    global NOTEBOOK_HOME
    global SHARED_HOME, LOGGER_HOME, AIRPORTS_DIR, AIRSPACES_DIR
    global BACKUPS_DIR, BUSINESS_LOGS_DIR
    global UPLOAD_DIR
    global JUPYTERHUB_USER, PYTHONPATH, MESSAGE_SERVER_PORT, MESSAGE_SERVER_HOST
    global COMPUTE_ENGINE_SERVICE_ACCOUNT, PEM_FILE, MESSAGE_SERVER_USER
    global MESSAGE_SERVER_PASSWORD

    PROJECT_NAME = env.get(PROJECT_NAME_ENV)
    BUCKET_NAME = env.get(BUCKET_NAME_ENV)
    PROJECT_HOME = env.get(PROJECT_HOME_ENV)
    PRU_HOME = env.get(PRU_HOME_ENV)
    DATA_HOME = env.get(DATA_HOME_ENV)
    SHARED_HOME = env.get(SHARED_HOME_ENV)
    LOGGER_HOME = env.get(LOGGER_HOME_ENV)
    NOTEBOOK_HOME = env.get(NOTEBOOK_HOME_ENV)

    # Data related
    AIRPORTS_DIR = env.get(AIRPORTS_ENV)
    AIRSPACES_DIR = env.get(AIRSPACES_ENV)
    BACKUPS_DIR = env.get(BACKUPS_ENV)
    BUSINESS_LOGS_DIR = env.get(BUSINESS_LOGS_ENV)
    UPLOAD_DIR = env.get(UPLOAD_ENV)

    # Jupyterhub specific values
    JUPYTERHUB_USER = env.get(JUPYTERHUB_USER_ENV)

    PYTHONPATH = env.get(PYTHONPATH_ENV)

    MESSAGE_SERVER_PORT = env.get(MESSAGE_SERVER_PORT_ENV)
    MESSAGE_SERVER_HOST = env.get(MESSAGE_SERVER_HOST_ENV)
    MESSAGE_SERVER_USER = env.get(MESSAGE_SERVER_USER_ENV)
    MESSAGE_SERVER_PASSWORD = env.get(MESSAGE_SERVER_PASSWORD_ENV)

    # Project related
    COMPUTE_ENGINE_SERVICE_ACCOUNT = env.get(COMPUTE_ENGINE_SERVICE_ACCOUNT_ENV)
    PEM_FILE = env.get(PEM_FILE_ENV)
