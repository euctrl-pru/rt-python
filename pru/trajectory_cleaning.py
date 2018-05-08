# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.
"""
Functions to clean trajectory position data.
"""

import numpy as np
from enum import IntEnum, unique
from .EcefPoint import distance_nm
from .ecef_functions import calculate_EcefPoints, calculate_leg_lengths
from .trajectory_functions import calculate_elapsed_times, calculate_min_speed

DEFAULT_MAX_SPEED = 750.0
'The maximum speed between positions, Knots'

DEFAULT_DISTANCE_ACCURACY = 0.25
'Maximum distance between points at the same time. Nautical Miles'

DEFAULT_TIME_PRECISION = 1.0
'The precision of the time stamps, one second'


@unique
class ErrorCounts(IntEnum):
    """The indicies of the error array."""
    TOTAL = 0
    DUPLICATE_POSITIONS = 1
    INVALID_ADDRESSES = 2
    INVALID_POSITIONS = 3
    INVALID_ALTITUDES = 4


def find_invalid_positions(points_df, *, max_speed=DEFAULT_MAX_SPEED,
                           distance_accuracy=DEFAULT_DISTANCE_ACCURACY,
                           time_precision=DEFAULT_TIME_PRECISION,
                           find_invalid_addresses=True):
    """
    Finds invalid positions in points_df.

    The function searches for:
        - duplicate positions with an aircraft address,
        - positions with a different aircraft address to the the flight,
        - horizontal positions which require an aircraft to fly over max_speed,
        - changes in vertical state from climbing to descending (or vice versa)
        without going through a level phase

    Invalid positions are set to True in the invalid_positions array.

    Parameters
    ----------
    points_df: a pandas DataFrame
        A DataFrame containing raw positions for a flight, sorted in time order.

    max_speed: float
        The maximum ground speed permitted between adjacent positions [Knots],
        default: 750 Knots.

    distance_accuracy: float
        The maximum distance between positions at the same time [Nautical Miles],
        default: 0.25 NM.

    time_precision: float
        The precision of time measurement [Seconds], default 1.0.

    find_invalid_addresses: bool
        A flag to enable/disable finding invalid aircraft addresses for testing.

    Returns
    -------

    invalid_positions : numpy bool array
        Invalid postions are set to True in this array.

    error_counts: array of ints
        Error counts are:
            - total number of invalid points
            - number of duplicate positions
            - number of invalid addresses
            - number of distance errors
            - number of altitude errors
    """
    # Duplicate positions with an aircraft address are invalid
    aircraft_address = points_df['AIRCRAFT_ADDRESS']
    invalid_positions = points_df.duplicated(
        subset=['TIME', 'LAT', 'LON', 'ALT',
                'AIRCRAFT_ADDRESS', 'SSR_CODE']).values & \
        (aircraft_address != '')

    # get the number of duplicate_positions
    duplicate_positions = np.count_nonzero(invalid_positions)

    # Different aircraft addresses are invalid
    invalid_addresses = 0
    aircraft_address = aircraft_address.loc[aircraft_address != '']
    address_counts = aircraft_address.value_counts()
    if find_invalid_addresses and (len(address_counts) > 1):
        # More than one aircraft address, mark the extra addresses as invalid
        for address in address_counts[1:].index:
            invalid_addr = (aircraft_address == address)
            invalid_addresses = np.count_nonzero(invalid_addr)
            invalid_positions |= invalid_addr

    # Calculate: positions, horizontal and vertical distances, etc.
    ecef_points = calculate_EcefPoints(points_df['LAT'].values,
                                       points_df['LON'].values)
    altitudes = points_df['ALT'].values
    times = calculate_elapsed_times(points_df['TIME'].values,
                                    points_df['TIME'].values[0])
    ssr_codes = points_df['SSR_CODE'].values

    # Counts of errors
    distance_errors = 0
    altitude_errors = 0
    ref_attitude = 0
    ref_i = 0  # The last known good index
    prev_i = 0  # The previous position index used
    for i in range(1, len(points_df)):
        # Only consider valid positions
        if not invalid_positions.iloc[i]:
            # Calculate speed from previous known good position
            distance = distance_nm(ecef_points[i], ecef_points[ref_i])
            delta_time = times[i] - times[ref_i]
            speed = calculate_min_speed(distance, delta_time,
                                        distance_accuracy, time_precision)

            invalid = False
            if speed > max_speed:
                invalid = True
                distance_errors += 1

            # The attitude is: 1, if climbing, -1 if descending and 0 if level
            attitude = altitudes[i] - altitudes[prev_i]
            attitude = 1 if (attitude > 0) else -1 if (attitude < 0) else 0

            # if the attitude has changed
            if ref_attitude != attitude:
                # and the SSR code hasn't
                if ssr_codes[i] == ssr_codes[ref_i]:
                    ref_attitude = attitude
                # but if the SSR code is definitely different
                elif ssr_codes[i] != ssr_codes[prev_i]:
                    invalid = True
                    altitude_errors += 1

            if invalid:  # Mark the position as invalid
                invalid_positions.iloc[i] = True
            else:  # update the last known good position
                ref_i = i

            # Update the previously used index
            prev_i = i

    return invalid_positions, [np.count_nonzero(invalid_positions),
                               duplicate_positions, invalid_addresses,
                               distance_errors, altitude_errors]
