# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A trajectory time profile.
"""

import numpy as np
import json
from scipy.interpolate import CubicSpline
from .trajectory_functions import calculate_value_reference, calculate_value


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

    def interpolate_by_distance(self, distances):
        """
        Interpolate elapsed_times at the distance values.

        Uses the scipy.interpolate.CubicSpline function to interpolate
        times at the required distances.

        Parameters
        ----------
        timep: a TimeProfile
            A TimeProfile object.

        distances: float array
            An ordered array of distances in [Nautical Miles].

        Returns
        -------
        times : float array
            The elapsed_times at the given distance values in [Seconds].
        """
        cs = CubicSpline(self.distances, self.elapsed_times)
        return cs(distances)

    def interpolate_by_elapsed_time(self, times):
        """
        Interpolate distances at the elapsed time values.

        Uses the scipy.interpolate.CubicSpline function to interpolate
        distances at the required elapsed times.

        Parameters
        ----------
        timep: a TimeProfile
            A TimeProfile object.

        times: float array
            An ordered array of elapsed_times in [Seconds].

        Returns
        -------

        distances : float array
            The distances at the given time values in [Nautical Miles].
        """
        cs = CubicSpline(self.elapsed_times, self.distances)
        return cs(times)

    def calculate_average_period(self, start_distance, finish_distance):
        """
        Calculate the average period between points between the distances.

        Parameters
        ----------
        start_distance, finish_distance: float
            The start and finish distances to cacluate the periods between in
            [Nautical Miles].

        Returns
        -------
        The average period between the points between the distances.
        Zero if not enough points between the distances.

        """
        av_period = 0.0
        if start_distance < finish_distance:
            start_index, start_ratio = calculate_value_reference(self.distances,
                                                                 start_distance)
            finish_index, finish_ratio = calculate_value_reference(self.distances,
                                                                   finish_distance)
            delta_index = finish_index - start_index
            if delta_index > 2:
                # time of first point after start
                first_time = calculate_value(self.elapsed_times, start_index + 1)
                # time of last point before finish
                last_time = calculate_value(self.elapsed_times, finish_index)
                delta_time = last_time - first_time
                av_period = delta_time / float(delta_index - 1)

        return av_period

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
