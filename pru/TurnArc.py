# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports turning arcs in Earth Centred Earth Fixed (ECEF) coordinates.
"""
import numpy as np
from numpy import sqrt, sin, cos, arccos, tan
from .EcefPoint import EcefPoint, SQ_MIN_LENGTH
from .EcefArc import EcefArc

MIN_TURN_ANGLE = np.deg2rad(1.0)
""" The minimum turn angle to model. """

MAX_TURN_ANGLE = np.deg2rad(150.0)
""" The maximum turn angle to model. """


# @pre_condition(turn_angle > MIN_TURN_ANGLE)
def calculate_radius(turn_angle, anticipation_distance):
    """
    Calculate the radius of a turn from it's angle and anticipation_distance.
    Note: turn_angle nust be positive and greater than MIN_TURN_ANGLE.

    Parameters
    ----------
    turn_angle: float
        The turn angle in [radians].

    anticipation_distance: float
        The turn anticipation distance in [radians].

    Returns
    -------
    The radius of the turn in [radians].
    """
    return anticipation_distance / tan(0.5 * turn_angle)


def calculate_arc_length(angle, anticipation_distance):
    """
    Calculate the length of the arc of a turn from it's angle and anticipation
    distance.

    Parameters
    ----------
    angle: float
        The turn angle in [radians].

    anticipation_distance: float
        The turn anticipation distance in [radians].

    Returns
    -------
    The radius of the turn in [radians].
    """
    turn_angle = np.abs(angle)
    if turn_angle > MIN_TURN_ANGLE:
        return turn_angle * calculate_radius(turn_angle, anticipation_distance)
    else:  # turn_angle is too small, calculate the straight distance
        return 2.0 * anticipation_distance


class TurnArc:
    """
    A class for the arc of a turn between two Great Circle arcs in ECEF
    coordinates.

    The class contains the start, end and centre points of the arc together
    with it's radius [radians] and (signed) angle [radians].
    """
    __slots__ = ('__coords', '__angle', '__radius')

    def __init__(self, inbound, outbound, distance):
        """
        Create a new Arc from the inbound and outbound route legs.

        Parameters
        ----------
        inbound, outbound: EcefArcs
            The inbound and outbound legs.
        distance: float
            The turn anticipation distance [radians].
        """
        self.__coords = np.zeros((3, 3), dtype=float)
        self.__coords[0] = outbound.a
        self.__coords[1] = outbound.a
        self.__coords[2] = outbound.a
        self.__angle = 0.0
        self.__radius = 0.0

        turn_angle = arccos(np.clip(np.dot(inbound.pole, outbound.pole), -1.0, 1.0))
        if MIN_TURN_ANGLE < turn_angle <= MAX_TURN_ANGLE:
            is_left_turn = inbound.cross_track_distance(EcefPoint(outbound.b)) > 0.0
            if is_left_turn:
                self.__angle = -turn_angle
            else:
                self.__angle = turn_angle
            self.__radius = calculate_radius(turn_angle, distance)

            start_point = inbound.position(inbound.length - distance)
            self.__coords[0] = start_point
            r = -self.__radius if (self.__angle > 0.0) else self.__radius
            self.__coords[1] = inbound.perp_position(start_point, r)
            self.__coords[2] = outbound.position(distance)

    @property
    def coords(self):
        'Accessor for the Turn Arc coordinates.'
        return self.__coords

    @property
    def start(self):
        'Accessor for the Turn Arc start point coordinates.'
        return self.__coords[0]

    @property
    def centre(self):
        'Accessor for the Turn Arc centre point coordinates.'
        return self.__coords[1]

    @property
    def finish(self):
        'Accessor for the Turn Arc end point coordinates.'
        return self.__coords[2]

    @property
    def angle(self):
        'Accessor for the Turn angle [radians].'
        return self.__angle

    @property
    def radius(self):
        'Accessor for the Turn radius [radians].'
        return self.__radius

    def __repr__(self):
        return 'TurnArc({},{},{})'. \
            format(self.__coords, self.__angle, self.__radius)

    def __str__(self):
        return 'TurnArc{},{},{}'. \
            format(EcefPoint(self.centre).to_lat_long(),
                   self.__angle, self.__radius)

    def __eq__(self, other):
        return (self.coords == other.coords).all() \
            and (self.angle == other.angle) \
            and (self.radius == other.radius)

    def __bool__(self):
        'Returns false if the radius is zero, true otherwise.'
        return bool(self.__radius > 0.0)

    def length(self):
        'Calculates the length of the turn arc [radians].'
        return self.__radius * np.abs(self.__angle)

    def radial_distance(self, point):
        """
        The distance of a point from the centre of the turn arc.

        Parameters
        ----------
        point: EcefPoint
            The point to measure.

        Returns
        -------
        distance: float
            The distance between point and the centre of the turn [radians].
        """
        return point.great_circle_distance(EcefPoint(self.centre))

    def cross_track_distance(self, point):
        """
        The distance of a point outside (+ve) or inside (-ve) the turn.

        Parameters
        ----------
        point: EcefPoint
            The point to measure.

        Returns
        -------
        distance: float
            The distance between point and the turn arc [radians].
        """
        return self.radial_distance(point) - self.radius

    def point_angle(self, point):
        """
        The angle of a point from the start of the turn arc.

        Parameters
        ----------
        point: EcefPoint
            The point to measure.

        Returns
        -------
        angle: float
            The angle between point and the start of the turn [radians].
        """
        radial_pole = np.cross(self.centre, point)
        radial_norm = np.dot(radial_pole, radial_pole)
        if SQ_MIN_LENGTH < radial_norm:
            radial_pole = radial_pole / sqrt(radial_norm)

            start_pole = np.cross(self.centre, self.start)
            start_norm = np.dot(start_pole, start_pole)
            start_pole = start_pole / sqrt(start_norm)

            angle = arccos(np.dot(start_pole, radial_pole))
            is_left_turn = np.dot(start_pole, point) > 0.0
            return -angle if is_left_turn else angle
        else:  # point is too near centre
            return 0.0

    def along_track_distance(self, point):
        """
        The distance of a point along the turn from the start of the arc.

        Parameters
        ----------
        point: EcefPoint
            The point to measure.

        Returns
        -------
        distance: float
            The (signed) distance between point and the start of the turn,
            +ve in the direction of the arc, -ve before the start [radians].
        """
        distance = self.radius * self.point_angle(point)
        return -distance if (self.angle < 0.0) else distance

    def position(self, angle):
        """
        Calcuate the position of a point along the TurnArc at angle from the
        start point.

        Parameters
        ----------
        angle: float
            The angle between point and the start of the turn [radians].

        Returns
        -------
            point: EcefPoint
            The point at angle from the start along the turn arc.
        """
        # Great Circle Arc from centre to start
        start_arc = EcefArc(EcefPoint(self.centre), EcefPoint(self.start))
        # A point pi/2 from the centre along the start_arc rotated by angle
        angle_pos = cos(angle) * np.cross(start_arc.pole, self.centre) \
            - sin(angle) * start_arc.pole

        # Create an EcefArc to angle_pos and calculate position at radius
        angle_arc = EcefArc(EcefPoint(self.centre), EcefPoint(angle_pos))
        return angle_arc.position(self.radius)
