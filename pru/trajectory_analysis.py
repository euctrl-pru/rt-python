# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to smooth trajectory position data.
"""

import numpy as np
import pandas as pd
import scipy.optimize
from via_sphere import global_Point3d
from pru.spherical_path_functions import derive_horizontal_path
from pru.trajectory_functions import calculate_delta_time, calculate_elapsed_times, \
    calculate_speed, find_duplicate_values, max_delta, rad2nm, find_most_extreme_value
from pru.AltitudeProfile import AltitudeProfile, AltitudeProfileType, \
    closest_cruising_altitude, find_cruise_sections, find_cruise_positions, \
    set_cruise_altitudes
from pru.HorizontalPath import HorizontalPath
from pru.TimeProfile import TimeProfile
from pru.SmoothedTrajectory import SmoothedTrajectory

DEFAULT_ACROSS_TRACK_TOLERANCE = 0.5
""" The default across track tolerance in Nautical Miles, 0.5 NM. """

DEFAULT_MOVING_MEDIAN_SAMPLES = 5
""" The number of samples for the moving median filter to consider. """

DEFAULT_MOVING_AVERAGE_SAMPLES = 3
""" The number of samples for the moving average filter to consider. """

DEFAULT_SPEED_MAX_DURATION = 120.0
""" The maximum time between positions for speed smoothing, seconds. """

MOVING_AVERAGE_SPEED = 'mas'

LM = 'lm'
TRF = 'trf'
DOGBOX = 'dogbox'

# The set of valid curve fit methods
CURVE_FIT_METHODS = {LM, TRF, DOGBOX}


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
            start = cruise_indicies[index] + 1
            stop = cruise_indicies[index + 1]
            if start < stop:
                cruise_altitude = closest_cruising_altitude(altitudes[start])
                delta_alts = altitudes[start: stop] - cruise_altitude
                cruise_deltas = np.append(cruise_deltas, delta_alts)

    return cruise_deltas


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

    # Only keep climbing and descending sections and ensure that cruise altitudes
    # are at cruising flight levels
    cruise_positions = find_cruise_positions(len(altitudes), cruise_indicies)
    altitudes = set_cruise_altitudes(altitudes, cruise_indicies)
    dists = distances[~cruise_positions]
    alts = altitudes[~cruise_positions]

    return AltitudeProfile(dists, alts), alt_sd, max_alt


def moving_average(x, N):
    """
    Calculate the moving average or running mean of a numpy array.

    It would use the pandas rolling_mean function. However, it's deprecated,
    so it uses the rolling.mean functions on a Series instead.
    @see https://stackoverflow.com/questions/13728392/moving-average-or-running-mean

    Parameters
    ----------
    x: numpy float array
        The values to smooth.

    Returns
    -------
        The smoothed values
        Note: the values at the start and end of the array are not smoothed.

    """
    if (N > 1) and (len(x) > N):
        means = pd.Series(x)
        M = N // 2
        x[M:-M] = means.rolling(N, center=True).mean()[M:-M]

    return x


def moving_median(x, N):
    """
    Calculate the moving median of a numpy array.

    Note: the moving median is robust to outliers than the moving average.
    See: https://en.wikipedia.org/wiki/Moving_average

    Parameters
    ----------
    x: numpy float array
        The values to smooth.

    Returns
    -------
        The smoothed values
        Note: the values at the start and end of the array are not smoothed.

    """
    if (N > 1) and (len(x) > N):
        means = pd.Series(x)
        M = N // 2
        x[M:-M] = means.rolling(N, center=True).median()[M:-M]

    return x


def calculate_ground_speeds(path_distances, elapsed_times, max_duration):
    """
    Calculate ground speeds considering the duration between positions.

    It smooths speeds for positions that are within max_duration of each other.

    Parameters
    ----------
    path_distances: numpy float array
        The distances along the path[Nautical Miles].

    elapsed_times: numpy float array
        The times from the first point [Seconds].

    max_duration: float
        The maximum duration to consider for smoothing [Seconds].

    Returns
    -------
        The smoothed ground speeds [Knots].

    """
    leg_lengths = np.ediff1d(path_distances, to_begin=[0])
    durations = np.ediff1d(elapsed_times, to_begin=[0])
    speeds = calculate_speed(leg_lengths, durations)

    # if more than two legs
    if len(leg_lengths) > 2:
        # Consider the first speed outside of the loop
        if (durations[1] < max_duration / 10.0):
            speeds[1] = calculate_speed(leg_lengths[1] + leg_lengths[2],
                                        durations[1] + durations[2])

        for i in range(2, len(leg_lengths) - 1):
            # if the durationis short and the speed is not between speeds either side
            if durations[i] < max_duration and \
                not (speeds[i - 1] <= speeds[i] <= speeds[i + 1]) or \
               not (speeds[i - 1] >= speeds[i] >= speeds[i + 1]):
                # calculate speed using the length and times either side
                speeds[i] = calculate_speed(leg_lengths[i] + leg_lengths[i + 1],
                                            durations[i] + durations[i + 1])

    return speeds


def smooth_times(path_distances, elapsed_times, N, M, max_duration):
    """
    Smooth elapsed times by calculating and smoothing ground speeds.

    Parameters
    ----------
    path_distances: numpy float array
        The path distances [Nautical Miles].

    elapsed_times: numpy float array
        The elapsed times from the first point [Seconds].

    N : integer
        The number of samples to consider for the moving median filter.
        It should be an odd positive number, 0 or 1 disables the filter.

    M : integer
        The number of samples to consider for the moving average filter.
        It should be an odd positive number, 0 or 1 disables the filter.

    max_duration: float
        The maximum time between points to smooth [Seconds].

    Returns
    -------
        The smnothed elapsed_times from the first position [seconds].

    """
    speeds = calculate_ground_speeds(path_distances, elapsed_times, max_duration)

    # Calculate the running mean of the speeds, if enabled and possible
    # Note: first speed is zero, so not used to calculate average
    if (N > 1) and (len(speeds) > N + 1):
        speeds[1:] = moving_median(speeds[1:], N)
    if (M > 1) and (len(speeds) > M + 1):
        speeds[1:] = moving_average(speeds[1:], M)

    # Calculate the durations between postions using the smoothed speeds
    leg_lengths = np.ediff1d(path_distances, to_begin=[0])
    new_durations = np.zeros(len(path_distances), dtype=float)
    new_durations[1:] = 3600.0 * leg_lengths[1:] / speeds[1:]

    return np.cumsum(new_durations)


def analyse_speeds(distances, times, duplicate_positions,
                   N=5, M=5, max_duration=DEFAULT_SPEED_MAX_DURATION):
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

    N : integer
        The number of samples to consider for the moving median filter, default 5.

    M : integer
        The number of samples to consider for the moving average filter, default 5.

    max_duration: float
        The maximum time between points to smooth, default 120 [Seconds].

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

    # Smooth the times
    smoothed_times = smooth_times(valid_distances, elapsed_times, N, M, max_duration)

    # Adjust for any offset introduced by smoothing
    delta_times = smoothed_times - elapsed_times
    mean_delta = np.sum(delta_times) / len(delta_times)
    smoothed_times = smoothed_times - mean_delta

    # Then calculate deltas from the adjusted mean times
    delta_times = smoothed_times - elapsed_times
    time_sd = delta_times.std()
    max_time_diff, max_time_index = find_most_extreme_value(delta_times)

    # Don't output duplicate positions in the time profile
    return TimeProfile(times[0], valid_distances, smoothed_times), \
        time_sd, max_time_diff, max_time_index


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
    max_time_diff, max_time_index = find_most_extreme_value(delta_times)

    # Don't output duplicate positions in the time profile
    return TimeProfile(times[0], valid_distances, smoothed_times), \
        time_sd, max_time_diff, max_time_index


def analyse_trajectory(flight_id, points_df, across_track_tolerance, method,
                       N=DEFAULT_MOVING_MEDIAN_SAMPLES, M=DEFAULT_MOVING_AVERAGE_SAMPLES,
                       max_duration=DEFAULT_SPEED_MAX_DURATION):
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

    method: string
        The smoothing method to use: 'mas', 'lm', 'trf' 'dogbox'

    N : integer
        The number of samples to consider for the speed moving median filter, default 5.

    M : integer
        The number of samples to consider for the speed moving average filter, default 5.

    max_duration: float
        The maximum time between points to smooth when calculating speed, default 120 [Seconds].

    Returns
    -------
    smoothed_trajectoy: SmoothedTrajectory
        The SmoothedTrajectory containing the flight id, smoothed horizontal path,
        time profile and altitude profile.

    metrics: list
        A list containing the flight id and trajectory quality metrics.

    """
    # calculate the position period as seconds per point
    times = points_df['TIME'].values
    duration = calculate_delta_time(times[0], times[-1])
    position_period = duration / (len(points_df) - 1)

    # convert across_track_tolerance to radians
    across_track_radians = np.deg2rad(across_track_tolerance / 60.0)
    ecef_points = global_Point3d(points_df['LAT'].values,
                                 points_df['LON'].values)

    # derive the EcefPath
    path = derive_horizontal_path(ecef_points, across_track_radians)
    horizontal_path_distances = rad2nm(path.path_distances())

    # Ensure that the path is long enough
    if horizontal_path_distances[-1] < across_track_tolerance:
        raise ValueError("Path is short")

    lats, lons = path.point_lat_longs()
    tads = path.turn_initiation_distances_nm()
    hpath = HorizontalPath(lats, lons, tads)

    # Calculate distances of positions along the ECEF path in Nautical Miles
    path_distances = rad2nm(path.calculate_path_distances(ecef_points,
                                                          across_track_radians))

    # Raise an exception if the path_distances are shorter than the horizontal_path
    horizontal_path_length = horizontal_path_distances[-1] - across_track_tolerance
    points_path_length = path_distances[-1]
    if points_path_length < horizontal_path_length:
        raise ValueError("Horizontal path distances are short")

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

    # calculate standard deviation and maximum across track error
    xtds = path.calculate_cross_track_distances(ecef_points,
                                                path_distances)
    xte_sd = xtds.std()
    max_xte, max_xte_index = find_most_extreme_value(xtds)
    max_xte = abs(max_xte)

    # Find duplicate positions, i.e. postions with across_track_tolerance of each other
    duplicate_positions = find_duplicate_values(sorted_path_distances,
                                                across_track_tolerance)

    # determine whether to smooth time with speed or scipy cuvre fit
    if method in CURVE_FIT_METHODS:
        timep, time_sd, max_time_diff, max_time_index = analyse_times(sorted_path_distances,
                                                                      sorted_df['time'].values,
                                                                      duplicate_positions, method)
    else:
        timep, time_sd, max_time_diff, max_time_index = analyse_speeds(sorted_path_distances,
                                                                       sorted_df['time'].values,
                                                                       duplicate_positions,
                                                                       N, M, max_duration)
    max_time_diff = abs(max_time_diff)

    altp, alt_sd, max_alt = analyse_altitudes(sorted_path_distances, altitudes,
                                              cruise_indicies)
    alt_profile_type = altp.type()

    # Calculate average periods in the climb, cruise and descent phases
    toc_distance = altp.top_of_climb_distance()
    tod_distance = altp.top_of_descent_distance()

    climb_period = timep.calculate_average_period(0.0, toc_distance)
    cruise_period = timep.calculate_average_period(toc_distance, tod_distance)
    descent_period = timep.calculate_average_period(tod_distance, timep.distances[-1])

    return SmoothedTrajectory(flight_id, hpath, timep, altp), \
        [flight_id, int(alt_profile_type), position_period, climb_period,
         cruise_period, descent_period, int(unordered), time_sd, max_time_diff,
         max_time_index, xte_sd, max_xte, max_xte_index, alt_sd, max_alt]
