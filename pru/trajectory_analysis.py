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
from pru.trajectory_functions import calculate_delta_time, calculate_elapsed_times, \
    calculate_speed, find_duplicate_values, max_delta
from pru.AltitudeProfile import AltitudeProfile, find_level_sections
from pru.HorizontalPath import HorizontalPath
from pru.TimeProfile import TimeProfile
from pru.SmoothedTrajectory import SmoothedTrajectory

DEFAULT_ACROSS_TRACK_TOLERANCE = 0.25
""" The default across track tolerance in Nautical Miles, 0.25 NM. """

MOVING_AVERAGE_SPEED = 'mas'

LM = 'lm'
TRF = 'trf'
DOGBOX = 'dogbox'

# The set of valid curve fit methods
CURVE_FIT_METHODS = {LM, TRF, DOGBOX}


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
            cruise_positions[start: stop] = True

    return cruise_positions


def calculate_cruise_delta_alts(altitudes, cruise_indicies):
    """
    Calculate altitude differences from cruising flight levels.

    Parameters
    ----------

    altitudes: float array
        An array of altitudes [feet]

    cruise_indicies: integer list
        A list of indicies of the starts and finishes of cruising sections.

    Returns
    -------
        A numpy array of differences between altitudes and the cruising
        altitiude while the aircraft was cruising.

        The array will be empty if there are no cruising sections.
    """
    cruise_deltas = np.empty(0, dtype=float)

    if cruise_indicies:
        for index in range(0, len(cruise_indicies), 2):
            start = cruise_indicies[index]
            stop = cruise_indicies[index + 1]
            cruise_altitude = closest_cruising_altitude(altitudes[start])
            delta_alts = altitudes[start: stop] - cruise_altitude
            cruise_deltas = np.append(cruise_deltas, delta_alts)

    return cruise_deltas


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

    alt_sd: the standard deviation of the cruising altitude error.
    max_alt: the maximum cruising altitude error.
    """
    alt_sd = 0.0
    max_alt = 0.0

    cruise_delta_alts = calculate_cruise_delta_alts(altitudes, cruise_indicies)
    if len(cruise_delta_alts):
        alt_sd = cruise_delta_alts.std()
        max_alt = max_delta(cruise_delta_alts)

    # Only keep climbing and descending sections
    cruise_positions = find_cruise_positions(len(altitudes), cruise_indicies)
    dists = distances[~cruise_positions]
    alts = altitudes[~cruise_positions]

    return AltitudeProfile(dists, alts), alt_sd, max_alt


def calculate_ground_speeds(path_distances, elapsed_times):
    """
    Calculate ground speeds in Knots from path distances and elapsed times.

    Parameters
    ----------
    path_distances: numpy float array
        The path distances [Nautical Miles].

    elapsed_times: numpy float array
        The elapsed times from the first point [Seconds].

    Returns
    -------
        The ground speeds [Knots].

    """
    leg_lengths = np.ediff1d(path_distances, to_begin=[0])
    durations = np.ediff1d(elapsed_times, to_begin=[0])
    return calculate_speed(leg_lengths, durations)


def smooth_times(path_distances, elapsed_times, *, max_duration=120.0):
    """
    Smooth elapsed times by using a filter to smooth ground speeds

    Parameters
    ----------
    path_distances: numpy float array
        The path distances [Nautical Miles].

    elapsed_times: numpy float array
        The elapsed times from the first point [Seconds].

    max_duration: float
        The maximum time between points to smooth, default 120 [Seconds].

    Returns
    -------
        The ground speeds [Knots].

    """
    leg_lengths = np.ediff1d(path_distances, to_begin=[0])
    durations = np.ediff1d(elapsed_times, to_begin=[0])
    new_durations = durations.copy()
    speeds = calculate_speed(leg_lengths, durations)

    # Consider the first point outside of the loop
    if (durations[1] < max_duration / 10.0):
        speeds[1] = calculate_speed(leg_lengths[1] + leg_lengths[2],
                                    durations[1] + durations[2])
        new_durations[1] = 3600.0 * leg_lengths[1] / speeds[1]

    for i in range(2, len(path_distances) - 1):
        if durations[i] < max_duration and \
            not (speeds[i - 1] <= speeds[i] <= speeds[i + 1]) or \
           not (speeds[i - 1] >= speeds[i] >= speeds[i + 1]):
            speeds[i] = calculate_speed(leg_lengths[i] + leg_lengths[i + 1],
                                        durations[i] + durations[i + 1])
            new_durations[i] = 3600.0 * leg_lengths[i] / speeds[i]

    return np.cumsum(new_durations)


def analyse_speeds(distances, times, duplicate_positions):
    """
    Create an TimeProfile and quality metrics.

    Cruise positions are calculated and removed from the arrays of
    distances and altitudes.

    Parameters
    ----------
    distances : numpy float array
        An array of distances [Nautical Miles]

    times: numpy datetime64 array
        An array of datetimes [seconds]

    duplicate_positions: numpy bool array
        An array indicating duplicate distance positions.

    Returns
    -------
    TimeProfile: the time profile.

    time_sd: the time standard deviation.

    max_time_diff: the maximum time difference.
    """
    # calculate time differences from the first time in seconds
    elapsed_times = calculate_elapsed_times(times, times[0])

    # attempt to fit a curve to the distances and times
    def polynomial_5d(x, a, b, c, d, e, f):
        return a * x**5 + b * x**4 + c * x**3 + d * x**2 + e * x + f
    popt, pcov = scipy.optimize.curve_fit(polynomial_5d, distances, elapsed_times,
                                          method='lm')

    # Smooth the times
    smoothed_times = smooth_times(distances, elapsed_times)

    # Adjust for any offset introduced by smoothing
    delta_times = smoothed_times - elapsed_times
    mean_delta = np.sum(delta_times) / len(delta_times)
    smoothed_times = smoothed_times - mean_delta

    delta_times = smoothed_times - elapsed_times
    time_sd = delta_times.std()
    max_time_diff = max_delta(delta_times)

    # Don't output duplicate positions in the time profile
    return TimeProfile(times[0], distances[~duplicate_positions],
                       smoothed_times[~duplicate_positions]), time_sd, max_time_diff


def analyse_times(distances, times, duplicate_positions, method=LM):
    """
    Create an TimeProfile and quality metrics.

    Cruise positions are calculated and removed from the arrays of
    distances and altitudes.

    Parameters
    ----------
    distances : numpy float array
        An array of distances [Nautical Miles]

    times: numpy datetime64 array
        An array of datetimes [seconds]

    duplicate_positions: numpy bool array
        An array indicating duplicate distance positions.

    Returns
    -------
    TimeProfile: the time profile.

    time_sd: the time standard deviation.

    max_time_diff: the maximum time difference.
    """
    # calculate time differences from non-duplicate positions
    elapsed_times = calculate_elapsed_times(times[~duplicate_positions], times[0])

    # dicatnces between non-duplicate positions
    valid_distances = distances[~duplicate_positions]

    # attempt to fit a curve to the distances and times
    # Using the Levenberg-Marquardt algorithm
    def polynomial_5d(x, a, b, c, d, e, f):
        return a * x**5 + b * x**4 + c * x**3 + d * x**2 + e * x + f
    popt, pcov = scipy.optimize.curve_fit(polynomial_5d, valid_distances, elapsed_times,
                                          method=method)
    # calculate time standard deviation
    time_sd = np.sqrt(np.sum(np.diag(pcov)))

    # Adjust times to smoothed times and output quality metrics
    smoothed_times = polynomial_5d(valid_distances, *popt)

    # calculate the maximum time difference
    delta_times = smoothed_times - elapsed_times
    max_time_diff = max_delta(delta_times)

    # Don't output duplicate positions in the time profile
    return TimeProfile(times[0], valid_distances, smoothed_times), \
        time_sd, max_time_diff


def analyse_trajectory(flight_id, points_df, across_track_tolerance, method=LM):
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
    duration = calculate_delta_time(times[0], times[-1])
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

    # calculate standard deviation and maximum across track error
    xtds = path.calculate_cross_track_distances(sorted_df['points'].values,
                                                sorted_path_distances)
    xte_sd = xtds.std()
    max_xte = max_delta(xtds)

    # Find duplicate positions, i.e. postions with across_track_tolerance of each other
    duplicate_positions = find_duplicate_values(sorted_path_distances,
                                                across_track_tolerance)

    # determine whether to smooth time with speed or scipy cuvre fit
    if method in CURVE_FIT_METHODS:
        timep, time_sd, max_time_diff = analyse_times(sorted_path_distances,
                                                      sorted_df['time'].values,
                                                      duplicate_positions, method)
    else:
        timep, time_sd, max_time_diff = analyse_speeds(sorted_path_distances,
                                                       sorted_df['time'].values,
                                                       duplicate_positions)

    altp, alt_sd, max_alt = analyse_altitudes(sorted_path_distances, altitudes,
                                              cruise_indicies)

    return SmoothedTrajectory(flight_id, hpath, timep, altp), \
        [flight_id, int(alt_profile_type), position_period, int(unordered),
         time_sd, max_time_diff, xte_sd, max_xte, alt_sd, max_alt]
