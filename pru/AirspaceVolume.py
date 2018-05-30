# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
Find intersections with a volume of airspace
"""


class AirspaceVolume:
    """
    A class for an airspace volume.
    """
    __slots__ = ('__name', '__bottom_altitude', '__top_altitude')

    def __init__(self, name, bottom_alt, top_alt):
        """ AirspaceVolume constructor """
        self.__name = name
        self.__bottom_altitude = bottom_alt
        self.__top_altitude = top_alt

    @property
    def name(self):
        return self.__name

    @property
    def bottom_altitude(self):
        return self.__bottom_altitude

    @property
    def top_altitude(self):
        return self.__top_altitude

    def is_inside(self, alt):
        """ Whether the altitude is within the range from botton to top. """
        return (self.bottom_altitude <= alt) \
            and (alt < self.top_altitude)

    def vertical_intersection(self, min_alt, max_alt):
        """ Whether the altitude range intersects the range from botton to top. """
        return (self.bottom_altitude <= max_alt) \
            and (min_alt < self.top_altitude)

    def bottom_intersection(self, min_alt, max_alt):
        """ Whether the altitude range spans the bottom altitude. """
        return min_alt < self.bottom_altitude < max_alt

    def top_intersection(self, min_alt, max_alt):
        """ Whether the altitude range spans the top altitude. """
        return min_alt < self.top_altitude < max_alt
