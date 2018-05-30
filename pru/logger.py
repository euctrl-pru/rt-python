# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
This is a python 3.6 module.  Path handling wrt posix paths is not fully
implemented in python 3.5

A python module that provides access to named configured loggers.

The config can either be in a custom logger home directory or the current
HOME directory as specified by the env vars LOGGER_HOME and HOME in that
order of preference.

If the LOGGER_HOME and the HOME are not set a message is printed to
the console and a default logger is supplied.

If the LOGGER_HOME or HOME are set but no logging.yaml file is found
we use a default logger

If no logger is found that matches the given name a default console
logger is returned with threshold set to WARNING.  This will write to
std err which should apear in the console.

Inside an exception handler, mylog.exception will include the exception
trace.

The url:
 https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial
contains helpful information on logger configuration and behaviour.
"""
import logging
import logging.config
import yaml
import sys
import threading
from os import environ as env
from pathlib import Path

LOGGER_HOME = 'LOGGER_HOME'
LOGGING_CONFIG_FILE_NAME = 'logging.yaml'

# Used to ensure we only run the configuration once.
lock = threading.Semaphore(1)


def join(loader, node):
    """
    Used in the logging.yaml to create a reusable refence to the logger home
    dir, this stops repitition of the same string in every file definition.
    """
    seq = loader.construct_sequence(node)
    return ''.join([str(i) for i in seq])


def get_logging_home(loader, node):
    """
    Used by the logging yaml file to get the logger home, this eliminates a
    hard coded path to the logging home in the yaml.
    """
    return env.get('LOGGER_HOME')


def _defaultConfig():
    """
    Sets up the fallback logging configuration.  We use ISO 8601 with no
    time zone.  See https://en.wikipedia.org/wiki/ISO_8601
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(asctime)s] [%(name)s.%(funcName)s:%(lineno)d]" +
        " %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S", stream=sys.stdout)


def _logger_init(config_file_name=LOGGING_CONFIG_FILE_NAME):
    """
    Configures the logging from a logging yaml file.
    The configuration is only created once, the lock semaphore object above
    is decremented on first access, and never released.  Any further
    attempts will skip the initialisation.
    """
    if lock.acquire(blocking=False):
        _defaultConfig()

        # If the LOGGER_HOME environment variable is NOT set, it uses defaults
        logConfigPath = env.get(LOGGER_HOME)
        if logConfigPath:
            logConfigPath += '/' + config_file_name

            path = Path(logConfigPath)
            if path.exists():
                try:
                    yaml.add_constructor('!join', join)
                    yaml.add_constructor('!get_logging_home', get_logging_home)
                    with open(path) as configFile:
                        yamlConfig = yaml.load(configFile.read())
                        logging.config.dictConfig(yamlConfig['logging'])
                        configFile.close()
                except Exception:
                    # We were unable to open or read the yaml file
                    # so create a default log config
                    # There is nothing to be done, the fall back will be the
                    # default config
                    print('The logger config file:',  config_file_name,
                          'could not be read, using default configuration.')
            else:
                # No logging configuration path could be established.
                # There is nothing to be done, the fall back will be the default
                # config
                print('The logger config file:',  config_file_name,
                      'could not be found, using default configuration.')


def logger(name=None):
    """
    Return a configured logger or the default logger.

    Example :logger(__name__)
    returns a logger for a module and package.

    """
    _logger_init()
    return logging.getLogger(name)
