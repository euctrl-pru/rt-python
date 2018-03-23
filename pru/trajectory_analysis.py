# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to smooth trajectory position data.
"""

from enum import IntEnum, unique
import numpy as np
import pandas as pd
import scipy.optimize
from pru.EcefPoint import rad2nm
from pru.horizontal_path_functions import derive_horizontal_path
from pru.ecef_functions import calculate_EcefPoints
from pru.AltitudeProfile import AltitudeProfile, find_level_sections
from pru.HorizontalPath import HorizontalPath
from pru.TimeProfile import TimeProfile
from pru.SmoothedTrajectory import SmoothedTrajectory

DEFAULT_ACROSS_TRACK_TOLERANCE = 0.25
""" The default across track tolerance in Nautical Miles, 0.25 NM. """


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
        If None, closest_cruising_altitude is called to calculate the
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
            else:
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
            for i in range(start, stop):
                cruise_positions[i] = True

    return cruise_positions


def classify_altitude_profile(altitudes, cruise_indicies):
    """
    Classify an altitude profile based upon the altitudes and cruise_indicies.

    Parameters
    ----------
    altitudes: int array
        An array of altitudes.

    Returns
    -------
    The AltitudeProfileType of the altitudes.
    """
    # only cruising if cruising over the whole trajectory
    if (len(cruise_indicies) == 2) and \
        (cruise_indicies[0] == 0) and \
            (cruise_indicies[-1] == len(altitudes) - 1):
        return AltitudeProfileType.CRUISING
    else:
        max_alt = altitudes.max()
        has_climb = (max_alt > altitudes[0])
        has_descent = (max_alt > altitudes[-1])
        if has_climb != has_descent:
            return AltitudeProfileType.CLIMBING if has_climb \
                else AltitudeProfileType.DESCENDING

    return AltitudeProfileType.CLIMBING_AND_DESCENDING


def analyse_altitudes(distances, altitudes, cruise_indicies):
    """
    Create an AltitudeProfile and quality metrics.

    Cruise positions are calculated and removed from the arrays of
    distances and altitudes.

    Parameters
    ----------
    distances : float array
        An array of distances [Nautical Miles]

    altitudes: float array
        An array of altitudes [feet]

    cruise_indicies: integer list
        A list of indicies of the starts and finishes of cruising sections.

    Returns
    -------
    AltitudeProfile: the altitude profile.

    alt_error: the RMS altitude error.
    """
    # Only keep climibg and descending sections
    cruise_positions = find_cruise_positions(len(altitudes), cruise_indicies)
    dists = distances[~cruise_positions]
    alts = altitudes[~cruise_positions]

    alt_error = 0.0
    return AltitudeProfile(dists, alts), alt_error


def analyse_times(distances, times):
    """
    Create an TimeProfile and quality metrics.

    Cruise positions are calculated and removed from the arrays of
    distances and altitudes.

    Parameters
    ----------
    distances : float array
        An array of distances [Nautical Miles]

    times: numpy datetime64 array
        An array of datetimes [seconds]

    Returns
    -------
    TimeProfile: the time profile.

    alt_error: the RMS altitude error.
    """
    # calculate time differences from the first time in seconds
    def elapsed_time(t):
        return (t - times[0]) / np.timedelta64(1, 's')
    elapsed_times = elapsed_time(times)

    # attempt to fit a curve to the distances and times
    def polynomial_5d(x, a, b, c, d, e, f):
        return a * x**5 + b * x**4 + c * x**3 + d * x**2 + e * x + f
    popt, pcov = scipy.optimize.curve_fit(polynomial_5d, distances, elapsed_times,
                                          method='lm')
    # Adjust times to smoothed times and output quality metrics
    smoothed_times = polynomial_5d(distances, *popt)

    # calculate time standard deviation
    time_sd = np.sqrt(np.sum(np.diag(pcov)))

    return TimeProfile(times[0], distances, smoothed_times), time_sd


def analyse_trajectory(flight_id, points_df, across_track_tolerance):
    """
    Analyses and smooths positions in points_df.

    The function:
        - derives the horizontal path from the points_df latitudes and longitudes,
        - calculates the average time between positions
        - determines positions where the aircraft was cruising
        - classifys the trajectories vertical profile
        - derives and smooths the time profile,
        - derives and smooths the altitude profile,
        - constructs and retruns a SmoothedTrajectory containing the flight id,
         smoothed horizontal path, time profile and altitude profile.

    Parameters
    ----------
    flight_id: string
        The id of the flight.

    points_df: a pandas DataFrame
        A DataFrame containing raw positions for a flight, sorted in time order.

    across_track_tolerance: float
        The maximum across track distance[Nautical Miles], default: 0.25 NM.

    Returns
    -------

    smoothed_trajectoy: SmoothedTrajectory
        The SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    metrics: list
        A list containing the flight id and trajectory quality metrics.
    """
    if len(points_df) < 2:
        raise ValueError('Trajectory only has one point!')

    # calculate the position period as seconds per point
    times = points_df['TIME_SOURCE'].values
    duration = (times[-1] - times[0]) / np.timedelta64(1, 's')
    position_period = duration / (len(points_df) - 1)

    # convert across_track_tolerance to radians
    threshold = np.deg2rad(across_track_tolerance / 60.0)

    ecef_points = calculate_EcefPoints(points_df['LAT'].values,
                                       points_df['LON'].values)

    # derive the EcefPath
    path = derive_horizontal_path(ecef_points, threshold)
    lats, lons = path.point_lat_longs()
    tads = path.turn_initiation_distances_nm()
    hpath = HorizontalPath(lats, lons, tads)

    # Calculate distances of positions along the ECEF path in Nautical Miles
    path_distances = rad2nm(path.calculate_path_distances(ecef_points))

    # Sort positions by path distance then time
    sorted_df = pd.DataFrame({'distance': path_distances,
                              'time': times,
                              'altitude': points_df['ALT'].values,
                              'points': ecef_points})
    sorted_df.sort_values(by=['distance', 'time'], inplace=True)

    # determine whether the position order has changed
    sorted_path_distances = sorted_df['distance'].values
    unordered = (path_distances != sorted_path_distances).any()

    # find the indicies of starts and finishes of cruising sections and
    # classify the trajectory altitude profile
    altitudes = sorted_df['altitude'].values
    cruise_indicies = find_cruise_sections(altitudes)
    alt_profile_type = classify_altitude_profile(altitudes, cruise_indicies)

    # calculate RMS across track error from path
    xtds = path.calculate_cross_track_distances(sorted_df['points'].values,
                                                sorted_path_distances)
    sq_xtds = xtds ** 2
    rms_xte = np.sqrt(np.sum(sq_xtds))

    timep, time_sd = analyse_times(sorted_path_distances,
                                   sorted_df['time'].values)

    altp, alt_error = analyse_altitudes(sorted_path_distances, altitudes,
                                        cruise_indicies)

    return SmoothedTrajectory(flight_id, hpath, timep, altp), \
        [flight_id, position_period, int(unordered), int(alt_profile_type),
         rms_xte, time_sd, alt_error]
