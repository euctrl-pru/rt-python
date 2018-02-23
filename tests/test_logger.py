# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
    Simple tests against the logger.  There are no asserttions in here.

    We use an alternate logging configuration file located on the test
    data path, we override the LOGGER_HOME to point to this location.
    Note that this does not alter the external environment, just the context
    of this test.

    All checks must be visual.

    The TEST_DATA_HOME must be set and contain a test logger config.
"""
import unittest
import pru.logger
import threading
import time
from pru.logger import logger as logger
from os import environ as env


LOGGER_HOME = pru.logger.LOGGER_HOME
LOGGING_CONFIG_FILE_NAME = pru.logger.LOGGING_CONFIG_FILE_NAME
logging_home = env.get(LOGGER_HOME)

TEST_DATA_HOME = 'TEST_DATA_HOME'
TEST_LOGGING_CONFIG_NAME = 'test-logging.yaml'
test_data_home = env.get(TEST_DATA_HOME)
TEST_LOGGING_HOME = test_data_home + "/" + "logging"
#env[LOGGER_HOME] = TEST_LOGGING_HOME


class TestLoggingErrorPaths(unittest.TestCase):
    def test_unknown_logger_name(self):
        # Unknown logger name should write to the console.
        # Check that the following two line appear in the console.
        env[LOGGER_HOME] = logging_home
        my_logger = logger('unknown')
        my_logger.info("Hello info unknown from " + __name__ +
                       ".TestLoggingErrorPaths." +
                       "test_unknown_logger_name")
        my_logger.warning("Hello warning from unknown " + __name__ +
                          ".TestLoggingErrorPaths." +
                          "test_unknown_logger_name")
        for i in range(20):
            my_logger = logger('unknown')
            my_logger.info("Hello info unknown from " + __name__ +
                           ".TestLoggingErrorPaths." +
                           "test_unknown_logger_name")
            my_logger.warning("Hello warning from unknown " + __name__ +
                              ".TestLoggingErrorPaths." +
                              "test_unknown_logger_name")

    def test_no_logger_name(self):
        # No logger name should write to the console
        # Check that the following line appears in the console.
        my_logger = logger()
        print(my_logger)
        my_logger.warning("Hello no name from " + __name__ +
                          ".TestLoggingErrorPaths." +
                          "test_no_logger_name")


"""
class TestLoggingDifferntConfig(unittest.TestCase):
    # Using a different config name, check that the
    # following lines appear in the configured files.
    # These tests use the module name to match the logger.
    def test_module_name(self):
        env[LOGGER_HOME] = TEST_LOGGING_HOME
        my_logger = logger(__name__, TEST_LOGGING_CONFIG_NAME)
        my_logger.info("Hello info from " + __name__ +
                       ".TestLoggingDifferntConfig." +
                       "test_module_name")
        my_logger.warning("Hello warning from" + __name__ +
                          ".TestLoggingDifferntConfig." +
                          "test_module_name")


class TestLoggingUnknownConfig(unittest.TestCase):

    def test_module_name_no_config(self):
        # This test provides an unknown configurtion file which causes the
        # logger to fall back to its default, check the following logs
        # appear in the console.
        my_logger = logger(__name__, 'no-name')
        my_logger.info("Hello info from " + __name__ +
                       ".TestLoggingUnknownConfig." +
                       "test_module_name_no_config")
        my_logger.warning("Hello warning from " + __name__ +
                          ".TestLoggingUnknownConfig." +
                          "test_module_name_no_config")

"""


class TestLoggingNormalFlowWithConfig(unittest.TestCase):
    def test_by_name(self):
        env[LOGGER_HOME] = TEST_LOGGING_HOME
        # The following lines should appear in the file configured by the
        # test logging config.
        my_logger = logger(__name__)
        my_logger.warning("Hello warning from" + __name__ +
                          ".TestLoggingNormalFlow." +
                          "test_by_name", )


class TestLoggingNormalFlowNoConfig(unittest.TestCase):
    def test_by_named_logger(self):
        env[LOGGER_HOME] = logging_home
        # The following lines should appear in the file configured by the
        # test logging config.
        my_logger = logger('util-logger')
        my_logger.warning("Hello warning from" + 'util-logger' +
                          ".TestLoggingNormalFlow." +
                          "test_by_name", )
        for i in range(10):
            my_logger = logger('util-logger')
            my_logger.warning("Hello warning from" + 'util-logger' +
                              ".TestLoggingNormalFlow." +
                              "test_by_name", )


class TestThreadLoggingNormalFlowNoConfig(unittest.TestCase):
    def test_by_threaded_named_logger(self):
        env[LOGGER_HOME] = ""#logging_home
        t_list = list()
        for t in range(20):
            thread = ThreadedLoggerClient(t, "Thread-" + str(t))
            thread.start()
            t_list.append(thread)
        for th in t_list:
            th.join()


class ThreadedLoggerClient(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        for i in range(10):
            this_logger = logger('util-logger')
            time.sleep(1)
            this_logger.info("Hello from thread " + self.name)


if __name__ == '__main__':
    unittest.main()
