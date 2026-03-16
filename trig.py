import math
from typing import Union

VECTOR_TWO = tuple

class Location:
    TAP_GROUP = 0
    A_GROUP = 1
    B_GROUP = 2
    C_GROUP = 3
    D_GROUP = 4
    E_GROUP = 5
    def __init__(self, index: int, group:int):
        self.index = index
        self.group = group

TAU = math.pi * 2

def vec_sub(a: VECTOR_TWO, b: VECTOR_TWO) -> VECTOR_TWO:
    return (a[0] - b[0], a[1] - b[1])

def vec_add(a: VECTOR_TWO, b: VECTOR_TWO) -> VECTOR_TWO:
    return (a[0] + b[0], a[1] + b[1])

def vec_mul(vec: VECTOR_TWO, scalar: float) -> VECTOR_TWO:
    return (vec[0] * scalar, vec[1] * scalar)

def vec_mag(vec: VECTOR_TWO) -> float:
    return math.sqrt(vec[0] ** 2 + vec[1] ** 2)

def rot_vec2(vector: VECTOR_TWO, rads: float) -> VECTOR_TWO:
    magnitude = vec_mag(vector)
    orig = math.atan2(vector[1], vector[0])

    new_degrees = orig + rads

    nx = math.cos(new_degrees) * magnitude
    ny = math.sin(new_degrees) * magnitude

    return (nx, ny)

def vec_rotate(vec: VECTOR_TWO, angle: float) -> VECTOR_TWO:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    x = vec[0] * cos_a - vec[1] * sin_a
    y = vec[0] * sin_a + vec[1] * cos_a
    return (x, y)

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def inverse_lerp(a: float, b: float, value: float) -> float:
    return (value - a) / (b - a)

def vec_lerp(a: VECTOR_TWO, b: VECTOR_TWO, t: float) -> VECTOR_TWO:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

def to_polar_ang(pos: VECTOR_TWO, offset: VECTOR_TWO | None = None):

    if offset is None:
        return math.atan2(pos[1], pos[0])
    
    diff = vec_sub(pos, offset)

    return math.atan2(diff[1], diff[0])

def get_tangent_angle_delta(adjacent: float, hypotenuse: float, clockwise: bool):
    angle_diff = math.acos(adjacent / hypotenuse)
    if clockwise:
        return -angle_diff
    else:
        return angle_diff

def get_angle_span(start_rotation: float, end_rotation: float, clockwise: bool, wrap_threshold: float | None = None):
    if wrap_threshold is None:
        wrap_threshold = TAU / 32
    if clockwise:
        span = (start_rotation - end_rotation + 2 * TAU) % TAU
    else:
        span = (end_rotation - start_rotation + 2 * TAU) % TAU
    
    if span <= wrap_threshold:
        span += TAU
    
    return span


class SlideGenerator:
    # edit these v
    PlayfieldRadius = 150
    AreaARadius = PlayfieldRadius * 1
    AreaBRadius = PlayfieldRadius * 0.533789634333
    CenterRadius = PlayfieldRadius * 0.222222222222
    AreaDRadius = PlayfieldRadius * 1
    AreaERadius = PlayfieldRadius * 0.709935208311
    RingRadius = PlayfieldRadius
    CurveRadius = PlayfieldRadius * math.sin(math.radians(22.5))
    # edit these ^
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("fixme")
    
    def get_rotation(self, location: Location) -> float:
        initial_angle = TAU / 4 - TAU / 16
        angle = initial_angle - (TAU / 8 * location.index)
        if location.group in (Location.D_GROUP, Location.E_GROUP):
            angle += TAU / 16
        return angle
    
    def get_position(self, location: Location) -> VECTOR_TWO:
        radius = self.get_radius_from_center(location)
        return self.get_position_radial(self.get_rotation(location), radius)
    
    def get_position_radial(self, rotation_rads: float, radius: float | None = None) -> VECTOR_TWO:
        if radius is None:
            radius = self.PlayfieldRadius
        x = math.cos(rotation_rads) * radius
        y = math.sin(rotation_rads) * radius
        return (x, y)
    
    def get_radius_from_center(self, location: Location) -> float:
        match location.group:
            case Location.TAP_GROUP:
                return self.PlayfieldRadius
            case Location.A_GROUP:
                return self.AreaARadius
            case Location.B_GROUP:
                return self.AreaBRadius
            case Location.C_GROUP:
                return 0
            case Location.D_GROUP:
                return self.AreaDRadius
            case Location.E_GROUP:
                return self.AreaERadius
            case _:
                raise ValueError(f"invalid location group {location.group}")
    
    def get_length(self) -> float:
        if hasattr(self, "total_length"):
            return self.total_length # type: ignore
        else:
            raise NotImplementedError("fixme")
    
    def get_point(self, time: float) -> Union[VECTOR_TWO, float]:
        raise NotImplementedError("fixme")