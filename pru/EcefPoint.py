# Copyright (c) 2017-2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

"""
This module supports points in Earth Centred Earth Fixed (ECEF) coordinates.
"""
import numbers
import numpy as np
from numpy import sqrt, sin, cos, arctan2

EPSILON = np.finfo(float).eps
""" The smallest value that can reasonably be measured. """

SQ_EPSILON = EPSILON ** 2
""" The square of the smallest value that can reasonably be measured. """

MIN_LENGTH = EPSILON * (2 ** 14)  # 16384
""" The minimum length of a vector to normalize. """

SQ_MIN_LENGTH = MIN_LENGTH ** 2
""" The square of the vector minimum length. """


class EcefPoint:
    """
    A class for an ECEF Point.
    ECEF points are spherical unit vectors, i.e.: x**2 + y**2 + z**2 = 1.0.
    Where x & y coordinates lie on the Equator and the z coordinate is along
    the polar axis, North positive.
    """
    __slots__ = ('__coords',)

    def __init__(self, coords):
        """
        Create an EcefPoint from x, y & z coordinates.

        Parameters
        ----------
        coords: x, y & z coordinates.
        """
        self.__coords = np.array(coords, dtype=float)

    @property
    def coords(self):
        'Accessor for the point coordinates.'
        return self.__coords

    @property
    def x(self):
        """
        Accessor for the x coordinate.
        On the plane of the equator: positive toward the Greenwich Meridian,
        negative toward the International Date Line.
        """
        return self.__coords[0]

    @property
    def y(self):
        """
        Accessor for the y coordinate.
        On the plane of the equator: East is positive, West is negative.
        """
        return self.__coords[1]

    @property
    def z(self):
        """
        Accessor for the z coordinate.
        On the line between the poles: Northern Hemishpere is positive,
        Southern Hemisphere is negative.
        """
        return self.__coords[2]

    @classmethod
    def from_lat_long(cls, latitude_longitude):
        """
        Create an EcefPoint from a Latitude and Longitude.
        Note: Latitudes > 90 are clamped to the North Pole.
              Latitudes < -90 are clamped to the South Pole.
              Latitudes > 180 or < -180 wrap around the International Date Line.

        Parameters
        ----------
        latitude_longitude: float
            A 2 element list of Latitude and Longitude in [degrees].
        """
        latitude = np.deg2rad(np.clip(latitude_longitude[0], -90.0, 90.0))
        longitude = np.deg2rad(latitude_longitude[1])

        sin_latitude = sin(latitude)
        cos_latitude = sqrt(1.0 - sin_latitude ** 2)
        x = cos_latitude * cos(longitude)
        y = cos_latitude * sin(longitude)
        z = sin_latitude

        return cls([x, y, z])

    def to_lat_long(self):
        """
        Converts an EcefPoint to a Latitude and Longitude.

        Returns
        -------
            latitude : float
                Latitude in [degrees].
            longitude : float
                Longitude in [degrees].
        """
        w = sqrt(self.x ** 2 + self.y ** 2)
        return np.rad2deg(arctan2(self.z, w)), np.rad2deg(arctan2(self.y, self.x))

    def __iter__(self):
        return iter(self.__coords)

    def __hash__(self):
        return hash(hash(self.x) ^ hash(self.y) ^ hash(self.z))

    def __repr__(self):
        return 'EcefPoint({})'.format(str(self.coords))

    def __str__(self):
        return 'EcefPoint{}'.format(self.to_lat_long())

    def __eq__(self, other):
        return (self.coords == other.coords).all()

    def norm(self):
        'The sum of the squares of the coordinates.'
        return np.dot(self.__coords, self.__coords)

    def __abs__(self):
        'The length of the vector.'
        return np.sqrt(self.norm())

    def __bool__(self):
        'Returns false if all coords are zero, true otherwise.'
        return bool(self.coords.any())

    def normalize(self):
        """
        Normalize an EcefPoint to lie on the surface of the sphere.

        Returns
        -------
            A normalized vector, i.e.: x^2 + y^2 + z^2 == 1.0
            Or a zero vector, if the input vector is too short.
        """
        sq_l = self.norm()
        if (SQ_MIN_LENGTH < sq_l):
            self.__coords = self.__coords / sqrt(sq_l)
        else:
            self.__coords = np.zeros(3, dtype=float)

    def __neg__(self):
        return EcefPoint(-self.__coords)

    def __pos__(self):
        return EcefPoint(self)

    def __add__(self, other):
        coords = self.__coords + other.__coords
        return EcefPoint(coords)

    def __sub__(self, other):
        coords = self.__coords - other.__coords
        return EcefPoint(coords)

    def __mul__(self, scalar):
        if isinstance(scalar, numbers.Real):
            return EcefPoint(scalar * self.__coords)
        else:
            return NotImplemented

    def __rmul__(self, scalar):
        return self * scalar

    def great_circle_distance(self, other):
        """
        The Great Circle distance between this and another EcefPoint.

        Returns
        -------
        distance: float
            The Great Circle distance between EcefPoints in [radians].
        """
        x = np.cross(self.coords, other.coords)
        sin_angle = np.sqrt(np.dot(x, x))
        cos_angle = np.dot(self.coords, other.coords)
        return arctan2(sin_angle, cos_angle)

    def __len__(self):
        return len(self.__coords)

    def __getitem__(self, index):
        cls = type(self)
        if isinstance(index, slice) or isinstance(index, numbers.Integral):
            return self.__coords[index]
        else:
            msg = '{cls.__name__} indicies must be integers'
            raise TypeError(msg.format(cls=cls))


def distance_radians(a, b):
    """
    The Great Circle distance between two EcefPoints: a and b.

    Parameters
    ----------
    a, b: EcefPoints.

    Returns
    -------
    distance: float
        The Great Circle distance between a and b in [radians].
    """
    return a.great_circle_distance(b)


def rad2nm(d):
    """
    Convert a distance in radians to Nautical Miles.
    Note: it assumes that the Earth is a sphere.

    Parameters
    ----------
    d: float.
    The distance in [radians].

    Returns
    -------
    The distance in [Nautical Miles].
    """
    return 60.0 * np.rad2deg(d)


def distance_nm(a, b):
    """
    The Great Circle distance between two EcefPoints: a and b.

    Parameters
    ----------
    a, b: EcefPoints.

    Returns
    -------
    distance: float
        The Great Circle distance between a and b in [Nautical Miles].
    """
    return rad2nm(distance_radians(a, b))
