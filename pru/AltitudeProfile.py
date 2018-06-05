# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
A trajectory altitude profile.
"""
from enum import IntEnum, unique
import numpy as np
import json
from scipy.interpolate import interp1d
from .trajectory_functions import calculate_value_reference, calculate_value


@unique
class AltitudeProfileType(IntEnum):
    """The types of altitude profile."""
    CRUISING = 0
    CLIMBING = 1
    DESCENDING = 2
    CLIMBING_AND_DESCENDING = 3


def closest_cruising_altitude(altitude):
    """
    Calculate the closest cruising altitude to the given altitude.

    Parameters
    ----------
    altitude: float
        An altitude [feet]

    Returns
    -------
    The closest cruising altitude to the given altitude.
    """
    return 1000 * ((altitude + 500) // 1000)


def is_cruising(altitude, cruise_altitude=None):
    """
    Determine whether an altitude may be a cruising altitude.

    Parameters
    ----------
    altitude: float
        An altitude [feet]

    cruise_altitude: float
        A cruise altitude [feet], default None.
        If None, -R  is called to calculate the
        nearest cruising altitude.

    Returns
    -------
    True if the altitiude is within tolerance of the cruising altitude,
    False otherwise.
    """
    if cruise_altitude is None:
        cruise_altitude = closest_cruising_altitude(altitude)
    return abs(altitude - cruise_altitude) <= 200


def in_cruise_level_range(altitudes, cruise_altitude):
    """
    Determine whether an altitude range may be at a cruising altitude.

    Parameters
    ----------
    altitudes: float array
        An array of altitudes[feet]

    cruise_altitude: float
        The cruise altitude [feet].

    Returns
    -------
    True if all altitiudes are within tolerance of the cruising altitude,
    False otherwise.
    """
    return is_cruising(altitudes, cruise_altitude).all()


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


def find_cruise_sections(altitudes):
    """
    Find pairs of start/finish indicies of altitudes where an aircraft was cruising.

    Parameters
    ----------
    altitudes: float array
        An array of altitudes[feet]

    Returns
    -------
    cruise_indicies: a list of indicies of the starts and finishes of
    cruising sections.
    """
    indicies = find_level_sections(altitudes)

    if indicies:
        prev_altitude = altitudes[indicies[0]]
        cruise_altitude = closest_cruising_altitude(prev_altitude)
        was_cruising = is_cruising(prev_altitude, cruise_altitude)
        prev_altitude = cruise_altitude if was_cruising else prev_altitude

        merge_indicies = []
        for index in range(2, len(indicies), 2):
            altitude = altitudes[indicies[index]]
            cruise_altitude = closest_cruising_altitude(altitude)
            if is_cruising(altitude, cruise_altitude):
                # If the aircraft cruised between the level ranges,
                if was_cruising and (prev_altitude == cruise_altitude) and \
                    in_cruise_level_range(altitudes[indicies[index - 1] + 1: indicies[index]],
                                          cruise_altitude):
                    # merge the level indicies
                    merge_indicies.append(index - 1)
                    merge_indicies.append(index)

                prev_altitude = cruise_altitude
                was_cruising = True
            else:  # level but not at a cruising level
                merge_indicies.append(index)
                merge_indicies.append(index + 1)
                prev_altitude = altitude
                was_cruising = False

        # merge the level indicies
        while merge_indicies:
            index = merge_indicies.pop()
            del indicies[index]

    return indicies


def find_cruise_positions(num_altitudes, cruise_indicies):
    """
    Create a numpy boolean array with all positions inbetween the starts and
    finishes of cruising sections marked as True.

    Note: the starts and finish positions of cruising sections are marked False.

    Parameters
    ----------
    cruise_indicies: a list of indicies of the starts and finishes of
    cruising sections.

    Returns
    -------
    cruise_positions: boolean array
        An array of booleans of cruising positions (i.e. duplicates).
    """
    cruise_positions = np.zeros(num_altitudes, dtype=bool)

    if cruise_indicies:
        for index in range(0, len(cruise_indicies), 2):
            start = cruise_indicies[index] + 1
            stop = cruise_indicies[index + 1]
            if start < stop:
                cruise_positions[start: stop] = True

    return cruise_positions


def set_cruise_altitudes(altitudes, cruise_indicies):
    """
    Set cruising altitudes to the closest cruising altitude.

    Parameters
    ----------

    altitudes: an array of altitudes

    cruise_indicies: a list of indicies of the starts and finishes of
    cruising sections.

    Returns
    -------
    altitudes: array
        The altitudes with cruising altitudes to the closest cruising altitude.
    """
    if cruise_indicies:
        for index in range(0, len(cruise_indicies), 2):
            start = cruise_indicies[index]
            stop = cruise_indicies[index + 1]
            if start < stop:
                cruise_altitude = closest_cruising_altitude(altitudes[start])
                altitudes[start] = cruise_altitude
                altitudes[stop] = cruise_altitude

    return altitudes


def classify_altitude_profile(altitudes):
    """
    Classify an altitude profile based on the altitudes.

    Parameters
    ----------
    altitudes: int array
        An array of altitudes.

    Returns
    -------
    The AltitudeProfileType of the altitudes.
    """
    max_alt = altitudes.max()
    has_climb = (max_alt > altitudes[0])
    has_descent = (max_alt > altitudes[-1])

    if has_climb or has_descent:
        if has_climb != has_descent:
            return AltitudeProfileType.CLIMBING if has_climb \
                else AltitudeProfileType.DESCENDING
        else:
            return AltitudeProfileType.CLIMBING_AND_DESCENDING
    else:
        return AltitudeProfileType.CRUISING


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

    def type(self):
        'Classify the altitude profile type based on the altitudes.'
        return classify_altitude_profile(self.altitudes)

    def interpolate(self, distances):
        """
        Interpolate altitudes at distance values.

        Uses the scipy.interpolate.interp1d function to linearly interpolate
        altitudes at the required distances.

        Parameters
        ----------
        distances: float array
            An ordered array of distances in [Nautical Miles].

        Returns
        -------
        alts : float array
            The interpolated altitudes at the given distances.
        """
        cs = interp1d(self.distances, self.altitudes, fill_value='extrapolate')
        return cs(distances)

    def altitude_range(self, start_distance, finish_distance):
        """
        Determine the range of altitudes between start_distance and finish_distance.

        Parameters
        ----------
        start_distance, finish_distance: float
            The start and finish distances in [Nautical Miles].

        Returns
        -------
        min_alt, max_alt : float
            The minimum and maximum alttiudes in [feet].
        """
        start_index, start_ratio = calculate_value_reference(self.distances,
                                                             start_distance)
        start_alt = calculate_value(self.altitudes, start_index, start_ratio)
        finish_index, finish_ratio = calculate_value_reference(self.distances,
                                                               finish_distance)
        finish_alt = calculate_value(self.altitudes, finish_index, finish_ratio)

        min_alt = min(start_alt, finish_alt)
        max_alt = max(start_alt, finish_alt)

        if start_index < finish_index:
            altitudes = self.altitudes[start_index + 1: finish_index + 1]
            min_alt = min(min_alt, altitudes.min())
            max_alt = max(max_alt, altitudes.max())

        return min_alt, max_alt

    def top_of_climb_index(self):
        """
        Determine the index of the top of climb altitude.

        Returns
        -------
        The index of the first cruising altitude.

        """
        return self.altitudes.argmax()

    def top_of_descent_index(self):
        """
        Determine the index of the top of climb altitude.

        Returns
        -------
        The index of the last cruising altitude.

        """
        tod = self.altitudes.argmax()
        # if the altitude profile is not just a climb
        # and there is a cruising section
        if (tod < len(self.altitudes) - 1) and \
                (self.altitudes[tod] == self.altitudes[tod + 1]):
            tod += 1

        return tod

    def top_of_climb_distance(self):
        """
        Determine the path distance of the top of climb altitude.

        Returns
        -------
        The path distance of the first cruising altitude.

        """
        return self.distances[self.top_of_climb_index()]

    def top_of_descent_distance(self):
        """
        Determine the path distance of the top of descent altitude.

        Returns
        -------
        The path distance of the first cruising altitude.

        """
        return self.distances[self.top_of_descent_index()]

    def intersection_distances(self, altitude, start_distance, finish_distance):
        """
        Calculate distances where the profile is at the given altitude.

        Parameters
        ----------

        altitude: float
            Tha altitude to find intersections with [feet].

        start_distance, finish_distance: float
            The start and finish distances of the section in [Nautical Miles].

        Returns
        -------
        distances : float
            The intersection distances in [Nautical Miles].
        """
        distances = []
        alt_index, alt_ratio = calculate_value_reference(self.distances,
                                                         start_distance)
        start_alt = calculate_value(self.altitudes, alt_index, alt_ratio)

        finish_index, finish_ratio = calculate_value_reference(self.distances,
                                                               finish_distance)
        while alt_index < finish_index:
            next_index = alt_index + 1
            next_ratio = 0.0
            next_alt = calculate_value(self.altitudes, next_index, next_ratio)

            # Does this section span the given altitude?
            if (next_alt != start_alt) and \
               (min(start_alt, next_alt) < altitude < max(start_alt, next_alt)):
                delta = altitude - start_alt
                denom = next_alt - start_alt
                ratio = delta / denom
                distance = calculate_value(self.distances, alt_index, ratio)
                distances.append(distance)

            alt_index = next_index
            alt_ratio = next_ratio
            start_alt = next_alt

        if finish_ratio:
            finish_alt = calculate_value(self.altitudes, finish_index, finish_ratio)
            # Does the last section span the given altitude?
            if (start_alt != finish_alt) and \
               (min(start_alt, finish_alt) < altitude < max(start_alt, finish_alt)):
                # Calculate the altitude at the end of the section to maximimse accuracy
                next_alt = calculate_value(self.altitudes, finish_index, 1.0)
                delta = altitude - start_alt
                denom = next_alt - start_alt
                ratio = delta / denom
                distance = calculate_value(self.distances, alt_index, ratio)
                distances.append(distance)

        return distances

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
