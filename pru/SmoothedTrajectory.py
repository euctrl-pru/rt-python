# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A Eurocontrol PRU smoothed trajectory.
"""

from .HorizontalPath import HorizontalPath
from .TimeProfile import TimeProfile
from .AltitudeProfile import AltitudeProfile


class SmoothedTrajectory:
    """
    A class to hold a smoothed trajectory.
    A smoothed trajectory consists of the horizontal path, timme profile and
    altitude profile of a flight.
    """
    __slots__ = ('__flight_id', '__path', '__timep', '__altp')

    def __init__(self, flight_id, path, timep, altp):
        'SmoothedTrajectory constructor'
        self.__flight_id = flight_id
        self.__path = path
        self.__timep = timep
        self.__altp = altp

    @property
    def flight_id(self):
        'Accessor for the flight_id.'
        return self.__flight_id

    @property
    def path(self):
        'Accessor for the path.'
        return self.__path

    @property
    def timep(self):
        'Accessor for the time profile.'
        return self.__timep

    @property
    def altp(self):
        'Accessor for the altp.'
        return self.__altp

    def dumps(self):
        'Dump the SmoothedTrajectory to a JSON string'
        string_list = ['{\n',
                       '    "flight_id" : "', str(self.flight_id), '",\n',
                       '    "horizontal_path" : ', self.path.dumps(), ',\n',
                       '    "time_profile" : ', self.timep.dumps(), ',\n',
                       '    "altitude_profile" : ', self.altp.dumps(), '\n',
                       '}']
        return ''.join(string_list)

    @classmethod
    def loads(cls, json_data):
        'Load a SmoothedTrajectory from a JSON object'
        flight_id = json_data["flight_id"]
        path = HorizontalPath.loads(json_data["horizontal_path"])
        timep = TimeProfile.loads(json_data["time_profile"])
        altp = AltitudeProfile.loads(json_data["altitude_profile"])
        return cls(flight_id, path, timep, altp)


def dumps_SmoothedTrajectories(trajs):
    'Dump a list of SmoothedTrajectories to a JSON string'
    string_list = ['{\n"data" : [\n']
    if len(trajs):
        string_list.append(trajs[0].dumps())
        for t in trajs[1:]:
            string_list.append(', ')
            string_list.append(t.dumps())

    string_list.append(']\n}\n')

    return ''.join(string_list)


def loads_SmoothedTrajectories(json_data):
    'Load a list of SmoothedTrajectories from a JSON object'
    trajectories = []
    for t in json_data['data']:
        trajectories.append(SmoothedTrajectory.loads(t))

    return trajectories
