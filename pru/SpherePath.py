# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports a trajectory path in Earth Centred Earth Fixed (ECEF)
coordinates.
"""

import numpy as np
from via_sphere import MIN_LENGTH, Arc3d, calculate_Arc3ds, \
    calculate_leg_lengths, calculate_turn_angles, \
    calculate_latitudes, calculate_longitudes, to_array
from .SphereTurnArc import SphereTurnArc, calculate_arc_length, \
    MIN_TURN_ANGLE, MAX_TURN_ANGLE
from .sphere_functions import find_index_and_ratio
from .trajectory_functions import calculate_value_reference, rad2nm


class PointType:
    """The types of EcefPath Points."""

    Waypoint, TurnStart, TurnFinish = range(3)


def calculate_arc_half_lengths(turn_angles, turn_initiation_distances):
    """
    Calculate the half lengths of arcs.

    Note: it only calculates arc lengths for non zero turn_initiation_distances.

    Parameters
    ----------
    turn_angles: float array
        An array of turn angles [radians]

    turn_initiation_distances: float array
        An array of turn initiation distances [radians]

    Returns
    -------
    lengths: a numpy array of half lengths of the arcs in [radians]

    """
    half_lengths = np.zeros(len(turn_angles), dtype=float)
    for i in range(len(turn_angles)):
        if turn_initiation_distances[i]:
            half_lengths[i] = calculate_arc_length(turn_angles[i],
                                                   turn_initiation_distances[i]) / 2
    return half_lengths


def calculate_paths_lengths(leg_lengths, turn_initiation_distances, arc_half_lengths):
    """
    Calculate the lengths of paths between waypoints.

    I.e. the leg_lengths shortend by (turn_initiation_distance - arc_half_length)
    at each waypoint.

    Parameters
    ----------
    leg_lengths: float array
        An array of distances between waypoints [radians]

    turn_initiation_distances: float array
        An array of turn initiation distances [radians]

    arc_half_lengths: float array
        An array of turn arc half lengths [radians]

    Returns
    -------
    lengths: a numpy array of path lengths in [radians]

    """
    lengths = np.zeros(len(leg_lengths), dtype=float)
    prev_delta = 0.0
    for i in range(1, len(leg_lengths) - 1):
        # delta is the shortened distance of the arc before the point
        delta = turn_initiation_distances[i] - arc_half_lengths[i]
        # subtract the shortening of the arcs at both ends of the leg
        lengths[i] = leg_lengths[i] - (prev_delta + delta)
        # the shortened distance of the arc after the point for the next leg
        prev_delta = delta

    # The last length can be shortend by the turn onto the leg
    lengths[-1] = leg_lengths[-1] - prev_delta

    return lengths


class SpherePath:
    """
    A class for an SpherePath Path.

    A SpherePath Path is an ordered collection of Points3D and their relative
    geometry: leg_lengths, turn_angles, path_lengths, etc.
    """

    __slots__ = ('__points', '__turn_initiation_distances', '__leg_lengths',
                 '__turn_angles', '__turn_half_lengths', '__path_lengths')

    # @pre(len(points) >= 2)
    # @pre(len(points) == len(turn_initiation_distances))
    def __init__(self, points, turn_initiation_distances):
        """
        Create a new SpherePath from points and turn_initiation_distances.

        There must be at least two points and the number of turn_initiation_distances
        must be equal to the number of points.

        All points must be at least MIN_LENGTH distance apart, otherwise a
        ValueError exeception is raised.

        All turn angles with a turn_initiation_distance must be less than the
        MAX_TURN_ANGLE.

        Parameters
        ----------
        points: Point3ds points.
            An ordered array of Point3ds.

        turn_initiation_distances: float array
            An ordered array of turn initiation distances [radians].

        """
        self.__points = points

        self.__turn_initiation_distances = turn_initiation_distances
        self.__leg_lengths = calculate_leg_lengths(points)

        # validate leg_lengths before constructing arcs
        # Note: first leg_length is zero
        has_a_short_leg = (self.__leg_lengths[1:].min() < MIN_LENGTH)
        if has_a_short_leg:
            raise ValueError('Some path points are closer than MIN_LENGTH.')

        leg_arcs = calculate_Arc3ds(points)

        # Calculate turn angles.
        turn_angles = calculate_turn_angles(leg_arcs)

        # clear turn_initiation_distances and turn angles for invalid turn angles
        for i in range(1, len(points) - 1):
            if not (MIN_TURN_ANGLE < abs(turn_angles[i]) <= MAX_TURN_ANGLE):
                self.__turn_initiation_distances[i] = 0.0
                turn_angles[i] = 0.0

        self.__turn_angles = turn_angles
        self.__turn_half_lengths = \
            calculate_arc_half_lengths(turn_angles, self.__turn_initiation_distances)
        self.__path_lengths = \
            calculate_paths_lengths(self.__leg_lengths, self.__turn_initiation_distances,
                                    self.__turn_half_lengths)

    @property
    def points(self):
        """Accessor for the points."""
        return self.__points

    @property
    def turn_initiation_distances(self):
        """Accessor for the turn_initiation_distances in [radians]."""
        return self.__turn_initiation_distances

    @property
    def leg_lengths(self):
        """Accessor for the leg_lengths in [radians]."""
        return self.__leg_lengths

    @property
    def turn_angles(self):
        """Accessor for the turn_angles in [radians]."""
        return self.__turn_angles

    @property
    def turn_half_lengths(self):
        """Accessor for the turn_half_lengths in [radians]."""
        return self.__turn_half_lengths

    @property
    def path_lengths(self):
        """Accessor for the path_lengths in [radians]."""
        return self.__path_lengths

    def __len__(self):
        """Get the number of points."""
        return len(self.points)

    def point_lat_longs(self):
        """Get the points as arrays of Latitudes and Longitudes in [degrees]."""
        return calculate_latitudes(self.points), calculate_longitudes(self.points)

    def turn_initiation_distances_nm(self):
        """Get the turn_initiation_distances in [Nautical Miles]."""
        return rad2nm(self.turn_initiation_distances)

    def path_distances(self):
        """
        Calculate distances along the path to the arc abeam points of the points.

        I.e. the distances along the path from the start point.

        Returns
        -------
        An ordered array of path distances [radians].

        """
        return np.cumsum(self.path_lengths)

    def turn_points(self, *, number_of_points=3):
        """
        Calculate the path flown along route legs and around turns.

        Parameters
        ----------
        number_of_points: integer
            The number of turn points to add between the start and end of each
            turn, default 3.

        Returns
        ----------
        An ordered array of points [Point3ds] containing the path flown
        along route legs and around turns.

        """
        # Add the path start point
        points = [self.points[0]]

        for i in range(1, len(self) - 1):
            turn_distance = self.turn_initiation_distances[i]
            if turn_distance:  # if there is a turn
                # Calculate the SphereTurnArc for the turn
                inbound_leg = Arc3d(self.points[i - 1], self.points[i])
                outbound_leg = Arc3d(self.points[i], self.points[i + 1])
                turn_arc = SphereTurnArc(inbound_leg, outbound_leg, turn_distance)
                if turn_arc:
                    # Add the turn start point
                    points.append(turn_arc.start)

                    if number_of_points:  # any indermediate points?
                        # calculate the angle between each point
                        delta_angle = turn_arc.angle / (1.0 + number_of_points)
                        angle = delta_angle
                        for j in range(number_of_points):  # create turn points
                            points.append(turn_arc.position(angle))
                            angle += delta_angle

                    # Add the turn finish point
                    points.append(turn_arc.finish)
                else:  # invalid turn_arc
                    points.append(self.points[i])
            else:  # no turn
                points.append(self.points[i])

        # Add the path finish point
        points.append(self.points[-1])

        return to_array(points)

    def calculate_position(self, index, ratio):
        """
        Calculate the position of a point along the path at index and ratio.

        It calculates whether the point is on a route leg or in a turn at either
        end of the route leg and then calculates the position accordingly.

        Parameters
        ----------
        index: integer
            The index of the point at the start of a route leg.

        ratio: ratio
            The ratio of the position as its distance along the path divided
            bu the path length. Note: 0.0 <= ratio < 1.0

        Returns
        -------
        The Point3d at index and ratio along the path.

        """
        # ensure index is within the points
        if index < len(self) - 1:
            # calculate the route leg arc
            arc = Arc3d(self.points[index], self.points[index + 1])

            #  calculate the distance from the point at index
            path_length = self.path_lengths[index + 1]
            distance = ratio * path_length

            # calcuate the distance to the turn by the next point
            next_turn_distance = path_length - self.turn_half_lengths[index + 1]

            # if point is in a Turn
            inside_start_turn = (self.turn_initiation_distances[index] > 0.0) and \
                (distance < self.turn_half_lengths[index])
            inside_finish_turn = (self.turn_initiation_distances[index + 1] > 0.0) and \
                (distance > next_turn_distance)
            if (inside_start_turn and (index > 0)) or \
                    (inside_finish_turn and (index < len(self) - 2)):
                inbound_leg = arc
                outbound_leg = arc
                turn_initiation_distance = self.turn_initiation_distances[index]
                if inside_finish_turn:
                    turn_initiation_distance = self.turn_initiation_distances[index + 1]
                    outbound_leg = Arc3d(self.points[index + 1], self.points[index + 2])
                    distance -= next_turn_distance
                    ratio = 0.5 * distance / self.turn_half_lengths[index + 1]
                else:  # inside_start_turn
                    inbound_leg = Arc3d(self.points[index - 1], self.points[index])
                    distance += self.turn_half_lengths[index]
                    ratio = 0.5 * distance / self.turn_half_lengths[index]

                # Calculate the position in the SphereTurnArc
                turn_arc = SphereTurnArc(inbound_leg, outbound_leg,
                                         turn_initiation_distance)
                return turn_arc.position(ratio * turn_arc.angle)
            else:  # point is along straight section
                # if the leg starts with a turn
                if self.turn_initiation_distances[index]:
                    distance += self.turn_initiation_distances[index] - \
                        self.turn_half_lengths[index]
                ratio = (distance / self.leg_lengths[index + 1])
                return arc.position(ratio * arc.length())

        else:  # return last point
            return self.points[-1]

    def calculate_path_leg_distance(self, point, index):
        """
        Calculate the distance of a point along a path leg starting at index.

        It calculates the along track distance along the leg starting at index.
        If the leg starts with a turn and the point is within it,
        the distance is the turn distance.
        If the leg finishes with a turn and the point is within it,
        the distance is the distance in the turn.
        Otherwise, if the leg starts with a turn, the distance is adjusted by
        the path length through the turn.

        Note: index must be within the points, i.e.: index < (len(self) - 1):

        Parameters
        ----------
        point: Point3d
            The point to measure.

        index: integer
            The index of the point at the start of the path leg.

        Returns
        -------
        The distance [radians] of the point along the path leg at index.

        """
        distance = 0.0

        # calculate the route leg arc and the point's distance along it
        arc = Arc3d(self.points[index], self.points[index + 1])
        distance = arc.along_track_distance(point)

        # if there is a start turn and the point is within it
        prev_turn_initiation_distance = self.turn_initiation_distances[index] \
            if (index > 0) else 0.0
        inside_prev_turn = (prev_turn_initiation_distance > 0.0) and \
            (distance < prev_turn_initiation_distance)
        if inside_prev_turn:
            inbound_leg = Arc3d(self.points[index - 1], self.points[index])
            turn_arc = SphereTurnArc(inbound_leg, arc, prev_turn_initiation_distance)
            distance = turn_arc.along_track_distance(point) \
                - self.turn_half_lengths[index]
        else:
            # calculate the distance to the turn by the next point
            next_turn_initiation_distance = self.turn_initiation_distances[index + 1]  \
                if (index < (len(self) - 2)) else 0.0
            next_turn_distance = arc.length() - next_turn_initiation_distance
            inside_next_turn = (next_turn_initiation_distance > 0.0) and \
                (distance > next_turn_distance)
            if inside_next_turn:
                outbound_leg = Arc3d(self.points[index + 1], self.points[index + 2])
                turn_arc = SphereTurnArc(arc, outbound_leg, next_turn_initiation_distance)
                distance = turn_arc.along_track_distance(point)
                distance += self.path_lengths[index + 1] \
                    - self.turn_half_lengths[index + 1]
            elif prev_turn_initiation_distance > 0.0:
                # point is along straight section that starts with a turn
                distance += self.turn_half_lengths[index] - prev_turn_initiation_distance

        return distance

    def calculate_path_distance(self, point, index, across_track_tolerance):
        """
        Calculate the distance of a point along the path by the leg at index.

        It determines whether the point is closer to the previous or next leg
        and calculates the path distance accordingly.

        Note: index must be within the points, i.e.: index < (len(self) - 1):

        Parameters
        ----------
        point: Point3d
            The point to measure.

        index: integer
            The index of the point at the start of the path leg.

        across_track_tolerance: float
            The maximum across track distance [radians]

        Returns
        -------
        The distance [radians] of the point along the path at index.

        """
        # calculate the closest distance between the point and the leg
        arc = Arc3d(self.points[index], self.points[index + 1])
        closest_distance = arc.closest_distance(point)

        prev_distance = closest_distance + 1.0
        if index > 0:  # not first leg
            # calculate the closest distance between the point and the previous leg
            arc = Arc3d(self.points[index - 1], self.points[index])
            prev_distance = arc.closest_distance(point)

        next_distance = closest_distance + 1.0
        if index < (len(self) - 2):  # not last leg
            # calculate the closest distance between the point and the next leg
            arc = Arc3d(self.points[index + 1], self.points[index + 2])
            next_distance = arc.closest_distance(point)

        min_distance = min(closest_distance, min(prev_distance, next_distance))
        if min_distance < across_track_tolerance:
            # Get the index of the closest leg
            if (prev_distance < closest_distance) \
                    or (next_distance < closest_distance):
                index = index - 1 if (prev_distance < next_distance) else index + 1
        else:  # None of the legs are within across_track_tolerance
            index, _ = find_index_and_ratio(self.points, point)
            index = min(index, len(self) - 2)

        # Calculate the path distance of the closest leg
        path_length = self.path_lengths[index + 1]
        distance = np.clip(self.calculate_path_leg_distance(point, index),
                           0.0, path_length)
        # Add the cumulative path lengths
        return distance + np.sum(self.path_lengths[:index + 1])

    def calculate_path_distances(self, ecef_points, across_track_tolerance,
                                 *, index=0):
        """
        Calculate the distances along the path to the ecef_points.

        The index is the index of the closest path leg to the first point.

        Parameters
        ----------
        ecef_points: Point3ds points.
            An ordered array of Point3ds.

        across_track_tolerance: float
            The maximum across track distance [radians]

        index: integer
            The index of the closest path leg  to the first point, default 0.

        Returns
        -------
        The distances along the path to each of the ecef_points in [radians].

        """
        distances = np.zeros(len(ecef_points), dtype=float)

        path_distance = self.path_lengths[index + 1]
        for i, point in enumerate(ecef_points):
            distances[i] = self.calculate_path_distance(point, index,
                                                        across_track_tolerance)
            past_current_leg = (distances[i] > path_distance)
            is_last_leg = (index >= len(self) - 2)
            if past_current_leg and not is_last_leg:
                # advance index and path_distance to the next leg
                index += 1
                path_distance += self.path_lengths[index + 1]

        return distances

    def find_index_and_ratio(self, point):
        """
        Find the index and ratio of the closest point along the path to point.

        Parameters
        ----------
        point: Point3d
            The point to find.

        Returns
        -------
        The index and ratio along the Path.

        If the point was not found: the index of the last point and zero
        respectively.

        """
        # find the index and ratio of the point along the route
        index, ratio = find_index_and_ratio(self.points, point)

        not_last_point = (index < (len(self) - 1))
        if not_last_point:
            distance = self.calculate_path_leg_distance(point, index)
            ratio = distance / self.path_lengths[index + 1]

            past_end = (ratio >= 1.0)
            if past_end:
                index += 1
                ratio = 0

                not_last_point = (index < (len(self) - 1))
                if not_last_point:
                    distance = self.calculate_path_leg_distance(point, index)
                    ratio = distance / self.path_lengths[index + 1]

        return index, ratio

    def calculate_path_cross_track_distance(self, point, index):
        """
        Calculate the cross track distance of a point from a path leg at index.

        It calculates the cross track distance from the leg starting at index.
        However, if the leg has turns at the ends and the point is within one
        of the turns, it calculates the cross track distance from the turn centre.

        Note: index must be within the points, i.e.: index < (len(self) - 1):

        Parameters
        ----------
        point: Point3d
            The point to measure.

        index: integer
            The index of the point at the start of the path leg.

        Returns
        -------
        The cross track distance [radians] of the point from the path leg at index.

        """
        # calculate the route leg arc and the point's distance from it
        arc = Arc3d(self.points[index], self.points[index + 1])
        xtd = arc.cross_track_distance(point)

        prev_turn_initiation_distance = self.turn_initiation_distances[index] \
            if (index > 0) else 0.0
        next_turn_initiation_distance = self.turn_initiation_distances[index + 1]  \
            if (index < (len(self) - 2)) else 0.0

        # if there is a turn at either end
        if (prev_turn_initiation_distance > 0.0) or \
                (next_turn_initiation_distance > 0.0):

            distance = arc.along_track_distance(point)
            inside_prev_turn = (prev_turn_initiation_distance > 0.0) and \
                (distance < prev_turn_initiation_distance)
            if inside_prev_turn:
                inbound_leg = Arc3d(self.points[index - 1], self.points[index])
                turn_arc = SphereTurnArc(inbound_leg, arc, prev_turn_initiation_distance)
                xtd = turn_arc.cross_track_distance(point)
            else:
                # calculate the distance to the turn by the next point
                next_turn_distance = arc.length() - next_turn_initiation_distance
                inside_next_turn = (next_turn_initiation_distance > 0.0) and \
                    (distance > next_turn_distance)
                if inside_next_turn:
                    outbound_leg = Arc3d(self.points[index + 1], self.points[index + 2])
                    turn_arc = SphereTurnArc(arc, outbound_leg, next_turn_initiation_distance)
                    xtd = turn_arc.cross_track_distance(point)

        return xtd

    def calculate_cross_track_distances(self, points, distances):
        """
        Calculate the across track distances of the points from the path.

        Parameters
        ----------
        points: Point3ds points array.
            An array of Point3ds in path distance order.

        distances: float array
            An array of order path distances of the points along the EcefPath
            in [Nautical Miles].

        Returns
        -------
        The cross track distances of the points from the path in [Nautical Miles].

        """
        xtds = np.zeros(len(points), dtype=float)

        path_index = 0
        path_distances_nm = rad2nm(np.cumsum(self.path_lengths))
        next_distance = path_distances_nm[path_index + 1]
        for i in range(len(points)):
            # Determine whether to advance the path_index
            if distances[i] > next_distance:
                if path_index < len(self) - 2:
                    path_index += 1
                    next_distance = path_distances_nm[path_index + 1]

            xtds[i] = rad2nm(self.calculate_path_cross_track_distance(points[i],
                                                                      path_index))
        return xtds

    def section_distances_and_types(self):
        """
        Calculate the distances to waypoints and starts/finishes of path turns.

        Returns
        -------
        The along path distances of waypoints and turns in [Nautical Miles].

        """
        distances = [0.0]
        point_types = [PointType.Waypoint]

        waypoint_distance = 0.0
        for i in range(1, len(self)):
            # Calculate the cumulative distance to the next waypoint
            # and the half length of the turn at the next waypoint (if any)
            waypoint_distance += self.path_lengths[i]
            turn_half_length = self.turn_half_lengths[i]
            if turn_half_length:  # if there is a turn
                # record the distance to the turn start
                distances.append(waypoint_distance - turn_half_length)
                point_types.append(PointType.TurnStart)

                # record the distance to the turn finish
                distances.append(waypoint_distance + turn_half_length)
                point_types.append(PointType.TurnFinish)
            else:  # no turn
                # record the distance to the waypoint
                distances.append(waypoint_distance)
                point_types.append(PointType.Waypoint)

        distances_nm = rad2nm(np.array(distances))

        return distances_nm, point_types

    def calculate_positions(self, distances):
        """
        Calculate the positions of points at distances along the path.

        Parameters
        ----------
        distances: float array
            An array of ordered path distances along the EcefPath in
            [Nautical Miles].

        Returns
        -------
        points: Point3ds points array.
            An array of Point3ds at distances along the path.

        """
        positions = []

        path_index = 0
        path_distance_nm = 0.0
        path_length_nm = rad2nm(self.path_lengths[path_index + 1])
        next_distance = path_distance_nm + path_length_nm
        for i in range(len(distances)):
            # Determine whether to advance the path_index
            if distances[i] > next_distance:
                if path_index < len(self) - 2:
                    path_index += 1
                    path_distance_nm += path_length_nm
                    path_length_nm = rad2nm(self.path_lengths[path_index + 1])
                    next_distance = path_distance_nm + path_length_nm

            # Calculate the ratio along the path leg
            ratio = (distances[i] - path_distance_nm) / path_length_nm
            position = self.calculate_position(path_index, ratio)
            positions.append(position)

        return to_array(positions)

    def subsection_positions(self, start_distance, finish_distance):
        """
        Return the points between start_distance and finish_distance.

        Parameters
        ----------
        start_distance: float
            The start distance along the EcefPath in Nautical Miles].

        finish_distance: float
            The finish distance along the EcefPath in Nautical Miles].

        Returns
        -------
        points: Point3ds points array.
            The array of Point3ds between start_distance and finish_distance
            including points at start_distance and finish_distance.

        """
        distances_nm = rad2nm(self.path_distances())
        start_index, start_ratio = calculate_value_reference(distances_nm,
                                                             start_distance)
        finish_index, finish_ratio = calculate_value_reference(distances_nm,
                                                               finish_distance)

        arc = Arc3d(self.points[start_index], self.points[start_index + 1])
        start_position = arc.position(start_ratio * arc.length())
        positions = [start_position]

        for i in range(start_index + 1, finish_index + 1):
            positions.append(self.points[i])

        if finish_ratio > 0.0:
            arc = Arc3d(self.points[finish_index], self.points[finish_index + 1])
            finish_position = arc.position(finish_ratio * arc.length())
            positions.append(finish_position)

        return to_array(positions)

    def calculate_ground_track(self, index, ratio):
        """
        Calculate the ground track of a point along the path at index and ratio.

        It calculates whether the point is on a route leg or in a turn at either
        end of the route leg and then calculates the ground track accordingly.

        Parameters
        ----------
        index: integer
            The index of the point at the start of a route leg.

        ratio: ratio
            The ratio of the position as its distance along the path divided
            bu the path length. Note: 0.0 <= ratio < 1.0

        Returns
        -------
        The ground track at index and ratio along the path in [radians].

        """
        # ensure index is within the points
        if index < len(self) - 1:
            # calculate the route leg arc
            arc = Arc3d(self.points[index], self.points[index + 1])

            #  calculate the distance from the point at index
            path_length = self.path_lengths[index + 1]
            distance = ratio * path_length

            # calcuate the distance to the turn by the next point
            next_turn_distance = path_length - self.turn_half_lengths[index + 1]

            # if point is in a Turn
            inside_start_turn = (self.turn_half_lengths[index] > 0.0) and \
                (distance < self.turn_half_lengths[index])
            inside_finish_turn = (self.turn_half_lengths[index + 1] > 0.0) and \
                (distance > next_turn_distance)
            if (inside_start_turn and (index > 0)) or \
                    (inside_finish_turn and (index < len(self) - 2)):
                inbound_leg = arc
                outbound_leg = arc
                turn_initiation_distance = self.turn_initiation_distances[index]
                if inside_finish_turn:
                    turn_initiation_distance = self.turn_initiation_distances[index + 1]
                    outbound_leg = Arc3d(self.points[index + 1], self.points[index + 2])
                    distance -= next_turn_distance
                    ratio = 0.5 * distance / self.turn_half_lengths[index + 1]
                else:  # inside_start_turn
                    inbound_leg = Arc3d(self.points[index - 1], self.points[index])
                    distance += self.turn_half_lengths[index]
                    ratio = 0.5 * distance / self.turn_half_lengths[index]

                turn_arc = SphereTurnArc(inbound_leg, outbound_leg, turn_initiation_distance)
                return inbound_leg.calculate_azimuth(turn_arc.start) \
                    + ratio * turn_arc.angle
            else:  # point is along straight section
                # if the leg starts with a turn
                if self.turn_initiation_distances[index]:
                    distance += self.turn_initiation_distances[index] - \
                        self.turn_half_lengths[index]
                ratio = (distance / self.leg_lengths[index + 1])
                point = arc.position(ratio * arc.length())
                return arc.calculate_azimuth(point)
        else:
            arc = Arc3d(self.points[-2], self.points[-1])
            return arc.calculate_azimuth(self.points[-1])

    def calculate_ground_tracks(self, distances):
        """
        Calculate the ground tracks of points at distances along the path.

        Parameters
        ----------
        distances: float array
            An array of ordered path distances along the EcefPath in
            [Nautical Miles].

        Returns
        -------
        ground_tracks: float array.
            An array of ground_tracks at distances along the path in [radians].

        """
        ground_tracks = np.zeros(len(distances), dtype=float)

        path_index = 0
        path_distance_nm = 0.0
        path_length_nm = rad2nm(self.path_lengths[path_index + 1])
        next_distance = path_distance_nm + path_length_nm
        for i in range(len(distances)):
            # Determine whether to advance the path_index
            if distances[i] > next_distance:
                if path_index < len(self) - 2:
                    path_index += 1
                    path_distance_nm += path_length_nm
                    path_length_nm = rad2nm(self.path_lengths[path_index + 1])
                    next_distance = path_distance_nm + path_length_nm

            # Calculate the ratio along the path leg
            ratio = (distances[i] - path_distance_nm) / path_length_nm
            ground_tracks[i] = self.calculate_ground_track(path_index, ratio)

        return ground_tracks
