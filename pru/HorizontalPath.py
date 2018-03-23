# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
The horizontal path of a smoothed trajectory.
"""

import numpy as np
import json


class HorizontalPath:
    """
    A class for a trajectory horizontal path.
    A horizontal path is the path followed by an aircraft including turns.
    """
    __slots__ = ('__lats', '__lons', '__tids')

    def __init__(self, lats, lons, tids):
        'HorizontalPath constructor'
        self.__lats = lats
        self.__lons = lons
        self.__tids = tids

    @property
    def lats(self):
        'Accessor for the latitudes.'
        return self.__lats

    @property
    def lons(self):
        'Accessor for the longitudes.'
        return self.__lons

    @property
    def tids(self):
        'Accessor for the turn initiation distances.'
        return self.__tids

    def dumps(self):
        'Dump the HorizontalPath to a JSON string'
        string_list = ['{\n',
                       '    "lats" : ', json.dumps(self.lats.tolist()), ',\n',
                       '    "lons" : ', json.dumps(self.lons.tolist()), ',\n',
                       '    "tids" : ', json.dumps(self.tids.tolist()), '\n',
                       '}']
        return ''.join(string_list)

    @classmethod
    def loads(cls, json_data):
        'Load an HorizontalPath from a JSON object'
        lats = np.array(json_data["lats"])
        lons = np.array(json_data["lons"])
        tids = np.array(json_data["tids"])
        return cls(lats, lons, tids)
