#!/usr/bin/env python3
import math, time, random

class ParameterStore:
    def __init__(self):
        self._params = {}

    def get(self, name, default=None):
        return self._params.get(name, default)

    def set(self, name, value):
        self._params[name] = value

class Trip():
    def __init__(self, start=0, end=0, Q=0, TC=0, VC=0, P=0):
        self.start = start
        self.end   = end
        self.Q     = Q
        self.TC    = TC
        self.VC    = VC
        self.P     = P   
        self.ATC   = TC/Q if Q > 0 else 0
        self.AVC   = VC/Q if Q > 0 else 0

class Robot:
    """
    Minimal robot object with a *param* field that supports
        • robot.param.get(...)
        • robot.param.set(...)
    """

    def __init__(self, id_number):
        self.id     = id_number
        self.param  = ParameterStore()
        self.trips  = []

class CustomTimer:
    def __init__(self):
        self.time_counter = 0

    def time(self):
        return self.time_counter

    def increase_timer(self):
        self.time_counter += 1

    def step(self):
        self.time_counter += 1

class Timer:
    def __init__(self, rate = 0, name = None):

        self.time  = CustomTimer()
        self.name  = name
        self.rate  = rate
        self.tick  = self.time.time()
        self.isLocked = False

    def query(self, reset = True):
        if self.remaining() <= 0:
            if reset: self.reset()
            return True
        else:
            return False

    def remaining(self):
        if type(self.rate) is int or type(self.rate) is float:
            return self.rate - (self.time.time() - self.tick)
        else:
            return 1

    def set(self, rate, reset = True):
        if not self.isLocked:
            self.rate = rate
            if reset:
                self.reset()
        return self

    def reset(self):
        if not self.isLocked:
            self.tick = self.time.time()
        return self

    def start(self):
        self.tick = self.time.time()
        self.isLocked = False

    def lock(self):
        self.isLocked = True
        return self

    def unlock(self):
        self.isLocked = False
        return self

class Resource(object):
    """ Establish the resource class 
    """
    def __init__(self, resource_js):
        # Required resource attrs: x, y, radius

        if isinstance(resource_js, dict):
            resource_dict = resource_js
        else:
            resource_dict = json.loads(resource_js.replace("\'", "\""))

        # Read the default resource attributes
        for attr in resource_dict:
            setattr(self, attr, resource_dict[attr])

        # Fix the number of decimals
        self.x = round(self.x, 2)
        self.y = round(self.y, 2)
        self.r = self.radius

        # Introduce the measurement error
        r = self.radius * math.sqrt(random.random()) * 0
        theta = 2 * math.pi * random.random()
        self._xr = self.x + r * math.cos(theta)
        self._yr = self.y + r * math.sin(theta)
        
        self._pr = (self._xr, self._yr)
        self._p  = (self.x, self.y)
        self._pv  = Vector2D(self.x, self.y)

        # Introduce the timestamp
        self._timeStamp = time.time()
        self._isSold = False
        self.param  = ParameterStore()

    @property
    def _json(self):
        public_vars = { k:v for k,v in vars(self).items() if not k.startswith('_')}
        return str(public_vars).replace("\'", "\"")

    @property
    def _dict(self):
        return { k:v for k,v in vars(self).items() if not k.startswith('_')}

    @property
    def _desc(self):
        return '{%s, %s, %s, %s}' % (self.x, self.y, self.quality, self.quantity)

    @property
    def _calldata(self):
        return (self.x, 
                self.y,  
                int(max(0,self.quantity)),
                int(self.utility), 
                str(self.quality), 
                str(self._json))

class Vector2D:
    """A two-dimensional vector with Cartesian coordinates."""

    def __init__(self, x = 0, y = 0, polar = False, degrees = False):

            self.x = x
            self.y = y

            if isinstance(x, (Vector2D, list, tuple)) and not y: 
                self.x = x[0]
                self.y = x[1]
            
            if degrees:
                y = math.radians(y)

            if polar:
                self.x = x * math.cos(y)
                self.y = x * math.sin(y)

            self.length = self.__abs__()
            self.angle = math.atan2(self.y, self.x)

    def __str__(self):
        """Human-readable string representation of the vector."""
        return '{:g}i + {:g}j'.format(self.x, self.y)

    def __repr__(self):
        """Unambiguous string representation of the vector."""
        return repr((self.x, self.y))

    def dot(self, other):
        """The scalar (dot) product of self and other. Both must be vectors."""

        if not isinstance(other, Vector2D):
            raise TypeError('Can only take dot product of two Vector2D objects')
        return self.x * other.x + self.y * other.y
    # Alias the __matmul__ method to dot so we can use a @ b as well as a.dot(b).
    __matmul__ = dot

    def cross(self, other):
        """The vector (cross) product of self and other. Both must be vectors."""

        if not isinstance(other, Vector2D):
            raise TypeError('Can only take cross product of two Vector2D objects')
        return abs(self) * abs(other) * math.sin(self-other)
    # Alias the __matmul__ method to dot so we can use a @ b as well as a.dot(b).
    __matmul__ = cross

    def __sub__(self, other):
        """Vector subtraction."""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        """Vector addition."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __radd__(self, other):
        """Recursive vector addition."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        """Multiplication of a vector by a scalar."""

        if isinstance(scalar, int) or isinstance(scalar, float):
            return Vector2D(self.x*scalar, self.y*scalar)
        raise NotImplementedError('Can only multiply Vector2D by a scalar')

    def __rmul__(self, scalar):
        """Reflected multiplication so vector * scalar also works."""
        return self.__mul__(scalar)

    def __neg__(self):
        """Negation of the vector (invert through origin.)"""
        return Vector2D(-self.x, -self.y)

    def __truediv__(self, scalar):
        """True division of the vector by a scalar."""
        return Vector2D(self.x / scalar, self.y / scalar)

    def __mod__(self, scalar):
        """One way to implement modulus operation: for each component."""
        return Vector2D(self.x % scalar, self.y % scalar)

    def __abs__(self):
        """Absolute value (magnitude) of the vector."""
        return math.sqrt(self.x**2 + self.y**2)

    def __round__(self, decimals):
        """Round the vector2D x and y"""
        return Vector2D(round(self.x, decimals), round(self.y, decimals))

    def __iter__(self):
        """Return the iterable object"""
        for i in [self.x, self.y]:
            yield i

    def __getitem__(self, index):
        """Return the iterable object"""
        if index == 0 or index == 'x':
            return self.x
        elif index == 1 or index == 'y':
            return self.y
        raise NotImplementedError('Vector2D is two-dimensional array (x,y)')


    def rotate(self, angle, degrees = False):
        if degrees:
            angle = math.radians(angle)
            
        return Vector2D(self.length, self.angle + angle, polar = True)

    def normalize(self):
        """Normalized vector"""
        if self.x == 0 and self.y == 0:
            return self
        else:
            return Vector2D(self.x/abs(self), self.y/abs(self))

    def distance_to(self, other):
        """The distance between vectors self and other."""
        return abs(self - other)

    def to_polar(self):
        """Return the vector's components in polar coordinates."""
        return self.length, self.angle
        
class mydict(dict):
    def __mul__(self, k):
        return mydict([[key, self[key] * k] for key in self])

    def __truediv__(self, k):
        return mydict([[key, self[key] / k] for key in self])

    def root(self, n):
        return mydict([[key, math.sqrt(self[key])] for key in self])

    def power(self, n):
        return mydict([[key, math.power(self[key])] for key in self])

    def round(self, n = 0):
        if n == 0:
            return mydict([[key, round(self[key])] for key in self])
        return mydict([[key, round(self[key], n)] for key in self])
