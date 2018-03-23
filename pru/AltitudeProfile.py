# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A trajectory altitude profile.
"""
import numpy as np
import json


def find_level_sections(alts):
    """
    Find pairs of start/finish indicies of consecutive altitudes with the same
    value. I.e. where an aircraft was in level flight.

    Parameters
    ----------
    alts: float array
        An array of altitudes[feet]

    Returns
    -------
    level_indicies: a list of indicies of the starts and finishes of
    level sections.
    """
    # Get the indicies of positions at the starts and end of levels
    level_indicies = []

    if len(alts) > 2:
        prev_alt = alts[0]
        alt = alts[1]

        # If the first two altitudea are the same, mark as is_level
        is_level = (prev_alt == alt)
        if is_level:
            level_indicies.append(0)

        for index in range(1, len(alts) - 1):
            next_alt = alts[index + 1]
            if is_level:
                # ignore single values at a different altitude
                is_level = (alt == next_alt)
                if not is_level:  # no longer is_level
                    # note the end cruise index
                    level_indicies.append(index)
            else:  # was not is_level
                is_level = (alt == next_alt)
                if is_level:
                    # note the start cruise index
                    level_indicies.append(index)

            # advance altitudes
            alt = next_alt
            prev_alt = alt

        # Ensure end is recorded if is_level
        if is_level:
            level_indicies.append(len(alts) - 1)

    return level_indicies


class AltitudeProfile:
    """
    A class for a trajectory altitude profile.
    A trajectory altitude profile is the altitude at distances along a path.
    """
    __slots__ = ('__distances', '__altitudes')

    def __init__(self, distances, altitudes):
        'AltitudeProfile constructor'
        self.__distances = distances
        self.__altitudes = altitudes

    @property
    def distances(self):
        'Accessor for the distances.'
        return self.__distances

    @property
    def altitudes(self):
        'Accessor for the altitudes.'
        return self.__altitudes

    def dumps(self):
        'Dump the AltitudeProfile to a JSON string'
        string_list = ['{\n',
                       '    "distances" : ', json.dumps(self.distances.tolist()), ',\n',
                       '    "altitudes" : ', json.dumps(self.altitudes.tolist()), '\n',
                       '}']
        return ''.join(string_list)

    @classmethod
    def loads(cls, json_data):
        'Load an AltitudeProfile from a JSON object'
        distances = np.array(json_data["distances"])
        altitudes = np.array(json_data["altitudes"])
        return cls(distances, altitudes)
