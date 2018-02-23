# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports Great Circle arcs in Earth Centred Earth Fixed (ECEF)
coordinates.
"""
import numpy as np
from numpy import sqrt, sin, cos, arcsin, arccos
from .EcefPoint import EcefPoint, EPSILON, SQ_EPSILON, MIN_LENGTH, SQ_MIN_LENGTH


class EcefArc:
    """
    A class for the arc of a Great Circle in ECEF coordinates.
    The arc of a Great Circle between two ECEF Points.
    """
    __slots__ = ('__coords', '__length')

    def __init__(self, a, b):
        """
        Create a new Arc from the start and finish points: a & b.
        Stores the start point and calculates and stores the pole of the
        Great Circle between the points and the length of the Arc.

        Parameters
        ----------
        a, b: 3d vectors
            The start and finish points.
        """
        self.__coords = np.zeros((2, 3), dtype=float)
        self.__coords[0] = a.coords
        p = EcefPoint(np.cross(a.coords, b.coords))
        p.normalize()
        self.__coords[1] = p.coords
        self.__length = a.great_circle_distance(b)

    @property
    def coords(self):
        'Accessor for the Arc start point and pole coordinates.'
        return self.__coords

    @property
    def length(self):
        'Accessor for the Arc length [radians].'
        return self.__length

    @property
    def a(self):
        'Accessor for the Arc start point coordinates.'
        return self.__coords[0]

    @property
    def pole(self):
        'Accessor for the Arc pole coordinates.'
        return self.__coords[1]

    def __repr__(self):
        return 'EcefArc({},{})'.format(self.__coords, (self.__length))

    def __eq__(self, other):
        return (self.coords == other.coords).all() \
            and (self.length == other.length)

    def __bool__(self):
        'Returns false if the pole is zero, true otherwise.'
        return bool(self.pole.any())

    def position(self, distance):
        """
        The position of a point at distance along the Arc.

        Parameters
        ----------
        distance: float
            The distance of the point along the Arc in [radians].

        Returns
        -------
        ecef_vector: list of 3 floats
            The point at the new position.

        """
        return EcefPoint(cos(distance) * self.a
                         + sin(distance) * np.cross(self.pole, self.a))

    @property
    def b(self):
        """
        Accessor for the Arc end point coordinates.
        """
        return self.position(self.length)

    def perp_position(self, point, distance):
        """
        The position of a perpendicuar point at distance from the Arc.

        Parameters
        ----------
        point: 3d vector
            A point on the Arc's Great Circle.
        distance: float
            The cross track distance of the point from the Arc in [radians].

        Returns
        -------
        ecef_vector: list of 3 floats
            The point at the new position.
        """
        return EcefPoint(cos(distance) * np.array(point)
                         + sin(distance) * self.pole)

    def cross_track_distance(self, point):
        """
        The across track distance of a point from the Arc.

        Parameters
        ----------
        point: 3d vector
            The point.

        Returns
        -------
        The across track distance of a point from the Arc in [radians]:
        positive to the left, negative to the right: -pi/2 <= xtd <= pi/2.
        """
        return arcsin(np.dot(self.pole, point))

    def along_track_distance(self, point):
        """
        The along track distance of a point along the Arc.

        Parameters
        ----------
        point: 3d vector
            The point.

        Returns
        -------
        The distance of a point along the Arc in [radians]:
        positive ahead of a, negative behind a: -pi <= atd <= pi.
        """
        # calculate distance from the Arc start point
        a = EcefPoint(self.a)
        atd = a.great_circle_distance(point)
        if atd > EPSILON and atd < (np.pi - EPSILON):
            # calculate across track distance magnitude
            sin2_xtd = np.dot(self.pole, point) ** 2
            cos2_xtd = 1.0 - sin2_xtd
            if cos2_xtd > SQ_EPSILON:
                if sin2_xtd > SQ_EPSILON:
                    cos_xtd = sqrt(cos2_xtd)
                    # calculate along track distance magnitude
                    atd = arccos(np.clip(cos(atd) / cos_xtd, -1.0, 1.0))

                # calculate the sign of the distance: +ve ahead, -ve behind
                ahead = np.dot(np.cross(self.pole, a), point)
                return -atd if (ahead < 0) else atd
            else:  # point is close to a pole of the Arc
                return 0.0
        else:  # point is close to the Arc start point or it's antipodal point
            return 0.0 if (atd <= EPSILON) else np.pi

    def closest_distance(self, point):
        """
        The closest distance of a point from the Arc.

        Parameters
        ----------
        point: 3d vector
            The point.

        Returns
        -------
        The closest distance of a point from the Arc in [radians].
        """
        atd = self.along_track_distance(point)
        if (0.0 <= atd <= self.length):
            return np.fabs(self.cross_track_distance(point))
        else:
            return min(point.great_circle_distance(EcefPoint(self.a)),
                       point.great_circle_distance(EcefPoint(self.b)))

    def turn_angle(self, point):
        """
        The turn angle from end of the Arc to the point.

        Parameters
        ----------
        point: 3d vector
            The point.

        Returns
        -------
        The turn angle from end of the Arc to the point in [radians].
        Note: anti-clockwise is negative.
        """
        b = EcefPoint(self.b)
        d = point.great_circle_distance(b)
        if (d > MIN_LENGTH):
            # calculate the pole of the arc to the point
            pole_p = EcefPoint(np.cross(b.coords, point.coords))
            pole_p.normalize()

            angle = np.arccos(np.clip(np.dot(self.pole, pole_p.coords), -1.0, 1.0))
            return -angle if (self.cross_track_distance(point) > 0.0) else angle
        else:
            return 0.0
