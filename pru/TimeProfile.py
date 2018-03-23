# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A trajectory time profile.
"""

import numpy as np
import json


class TimeProfile:
    """
    A class for a trajectory time profile.
    A trajectory time profile is the times at distances along a path.
    """
    __slots__ = ('__start_time', '__distances', '__elapsed_times')

    def __init__(self, start_time, distances, elapsed_times):
        'TimeProfile constructor'
        self.__start_time = start_time
        self.__distances = distances
        self.__elapsed_times = elapsed_times

    @property
    def start_time(self):
        'Accessor for the start_time.'
        return self.__start_time

    @property
    def distances(self):
        'Accessor for the distances.'
        return self.__distances

    @property
    def elapsed_times(self):
        'Accessor for the elapsed_times.'
        return self.__elapsed_times

    def dumps(self):
        'Dump the TimeProfile to a JSON string'
        string_list = ['{\n',
                       '    "start_time" : "', str(self.start_time), '",\n',
                       '    "distances" : ', json.dumps(self.distances.tolist()), ',\n',
                       '    "elapsed_times" : ', json.dumps(self.elapsed_times.tolist()), '\n',
                       '}']
        return ''.join(string_list)

    @classmethod
    def loads(cls, json_data):
        'Load a TimeProfile from a JSON object'
        start_time = np.datetime64(json_data["start_time"])
        distances = np.array(json_data["distances"])
        elapsed_times = np.array(json_data["elapsed_times"])
        return cls(start_time, distances, elapsed_times)
