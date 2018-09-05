# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports turning arcs in Spherical Vector coordinates.
"""
import numpy as np
from via_sphere import distance_radians, Arc3d

MIN_TURN_ANGLE = np.deg2rad(1.0)
""" The minimum turn angle to model. """

MAX_TURN_ANGLE = np.deg2rad(150.0)
""" The maximum turn angle to model. """


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
    return anticipation_distance / np.tan(0.5 * turn_angle)


def calculate_arc_length(angle, anticipation_distance):
    """
    Calculate the length of a turn arc from it's angle and anticipation distance.

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


class SphereTurnArc:
    """
    A class for the arc of a turn between two Great Circle arcs in ECEF coordinates.

    The class contains the start, end and centre points of the arc together
    with it's radius [radians] and (signed) angle [radians].
    """

    __slots__ = ('__start', '__centre', '__finish', '__angle', '__radius')

    def __init__(self, inbound, outbound, distance):
        """
        Create a new Arc from the inbound and outbound route legs.

        Parameters
        ----------
        inbound, outbound: Arc3ds
            The inbound and outbound legs.
        distance: float
            The turn anticipation distance [radians].

        """
        self.__start = outbound.a()
        self.__centre = outbound.a()
        self.__finish = outbound.a()
        self.__angle = 0.0
        self.__radius = 0.0

        self.__angle = inbound.turn_angle(outbound.b())
        turn_angle = abs(self.__angle)
        if MIN_TURN_ANGLE < turn_angle <= MAX_TURN_ANGLE:
            self.__radius = calculate_radius(turn_angle, distance)

            start_point = inbound.position(inbound.length() - distance)
            self.__start = start_point
            r = -self.__radius if (self.__angle > 0.0) else self.__radius
            self.__centre = inbound.perp_position(start_point, r)
            self.__finish = outbound.position(distance)
        else:
            self.__angle = 0.0

    @property
    def start(self):
        """Accessor for the Turn Arc start point."""
        return self.__start

    @property
    def centre(self):
        """Accessor for the Turn Arc centre point."""
        return self.__centre

    @property
    def finish(self):
        """Accessor for the Turn Arc end point."""
        return self.__finish

    @property
    def angle(self):
        """Accessor for the Turn angle [radians]."""
        return self.__angle

    @property
    def radius(self):
        """Accessor for the Turn radius [radians]."""
        return self.__radius

    def __eq__(self, other):
        """Return True if the centre, angle and radius are the same, False otherwise."""
        return (self.centre == other.centre)  \
            and (self.angle == other.angle) \
            and (self.radius == other.radius)

    def __bool__(self):
        """Return False if the radius is zero, True otherwise."""
        return bool(self.__radius > 0.0)

    def length(self):
        """Calculate the length of the turn arc [radians]."""
        return self.__radius * np.abs(self.__angle)

    def radial_distance(self, point):
        """
        Calculate the distance of a point from the centre of the turn arc.

        Parameters
        ----------
        point: Point3d
            The point to measure.

        Returns
        -------
        distance: float
            The distance between point and the centre of the turn [radians].

        """
        return distance_radians(self.centre, point)

    def cross_track_distance(self, point):
        """
        Calculate the distance of a point outside (+ve) or inside (-ve) the turn.

        Parameters
        ----------
        point: Point3d
            The point to measure.

        Returns
        -------
        distance: float
            The distance between point and the turn arc [radians].

        """
        return self.radial_distance(point) - self.radius

    def point_angle(self, point):
        """
        Calculate the angle of a point from the start of the turn arc.

        Parameters
        ----------
        point: Point3d
            The point to measure.

        Returns
        -------
        angle: float
            The angle between point and the start of the turn [radians].

        """
        start_arc = Arc3d(self.centre, self.start)
        return start_arc.start_angle(point)

    def along_track_distance(self, point):
        """
        Calculate the distance of a point along the turn from the start of the arc.

        Parameters
        ----------
        point: Point3d
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
        Calcuate the position of a point along the turn at angle from the start point.

        Parameters
        ----------
        angle: float
            The angle between point and the start of the turn [radians].

        Returns
        -------
            point: Point3d
            The point at angle from the start along the turn arc.

        """
        start_arc = Arc3d(self.centre, self.start)
        return start_arc.angle_position(angle)
