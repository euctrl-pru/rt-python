# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A Eurocontrol PRU smoothed trajectory.
"""
import json
from .HorizontalPath import HorizontalPath
from .TimeProfile import TimeProfile
from .AltitudeProfile import AltitudeProfile

SMOOTHED_TRAJECTORY_JSON_FOOTER = ']\n}\n'
"""The footer string for a JSON collection of SmoothedTrajectories."""


class SmoothedTrajectory:
    """
    A class to hold a smoothed trajectory.

    A smoothed trajectory consists of the horizontal path, timme profile and
    altitude profile of a flight.
    """

    __slots__ = ('__flight_id', '__path', '__timep', '__altp')

    def __init__(self, flight_id, path, timep, altp):
        """Constructor."""
        self.__flight_id = flight_id
        self.__path = path
        self.__timep = timep
        self.__altp = altp

    @property
    def flight_id(self):
        """Accessor for the flight_id."""
        return self.__flight_id

    @property
    def path(self):
        """Accessor for the path."""
        return self.__path

    @property
    def timep(self):
        """Accessor for the time profile."""
        return self.__timep

    @property
    def altp(self):
        """Accessor for the altitude profile."""
        return self.__altp

    def dumps(self):
        """Dump the SmoothedTrajectory to a list of JSON strings."""
        string_list = ['{\n',
                       '    "flight_id" : "', str(self.flight_id), '",\n',
                       '    "horizontal_path" : ', self.path.dumps(), ',\n',
                       '    "time_profile" : ', self.timep.dumps(), ',\n',
                       '    "altitude_profile" : ', self.altp.dumps(), '\n',
                       '}']
        return string_list

    @classmethod
    def loads(cls, json_data):
        """Load a SmoothedTrajectory from a JSON object."""
        flight_id = json_data["flight_id"]
        path = HorizontalPath.loads(json_data["horizontal_path"])
        timep = TimeProfile.loads(json_data["time_profile"])
        altp = AltitudeProfile.loads(json_data["altitude_profile"])
        return cls(flight_id, path, timep, altp)


def write_SmoothedTrajectories_json_header(method, tolerance, N, M, max_speed_duration):
    """Write a SmoothedTrajectories header to a JSON string."""
    string_list = ['{\n"method" : "', method,
                   '",\n"distance_tolerance" : ', str(tolerance),
                   ',\n"moving_median_samples" : ', str(N),
                   ',\n"moving_average_samples" : ', str(M),
                   ',\n"max_speed_duration" : ', str(max_speed_duration),
                   ',\n"data" : [\n']
    return ''.join(string_list)


def dumps_SmoothedTrajectories(trajs, method, tolerance, N, M, max_speed_duration):
    """Dump a list of SmoothedTrajectories to a JSON string."""
    string_list = [write_SmoothedTrajectories_json_header(method, tolerance, N, M,
                                                          max_speed_duration)]
    if len(trajs):
        string_list += trajs[0].dumps()
        for t in trajs[1:]:
            string_list.append(', ')
            string_list += t.dumps()

    string_list.append(SMOOTHED_TRAJECTORY_JSON_FOOTER)

    return ''.join(string_list)


def loads_SmoothedTrajectories(json_data):
    """Load a list of SmoothedTrajectories from a JSON object."""
    trajectories = []
    for t in json_data['data']:
        trajectories.append(SmoothedTrajectory.loads(t))

    return trajectories


def generate_SmoothedTrajectories(filename):
    """
    Generate SmoothedTrajectories from a JSON file.

    A python generator function to read a JSON file containing
    SmoothedTrajectories, one trajectory at a time to minimise memory use.
    """
    with open(filename) as file:
        # Skip the JSON trajectories header
        line = next(file)
        line = next(file)
        while line[0] != '{':
            line = next(file)

        # The list of JSON line representing a SmoothedTrajectory
        line_buffer = []
        while line:
            # If this line is the end of SmoothedTrajectory
            if (line[0] == '}') and (len(line) < 3):
                # A short object indictaes the end of SmoothedTrajectories
                if len(line_buffer) < 2:
                    break

                line_buffer.append('}}')
                json_data = json.loads(''.join(line_buffer))
                yield SmoothedTrajectory.loads(json_data)

                # skip the next line and reset the line_buffer
                line = next(file)
                line_buffer = ['{']
            else:  # just add the line to the end of the buffer
                line_buffer.append(line)

            line = next(file)
