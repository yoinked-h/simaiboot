import trig
from trig import VECTOR_TWO, Location, SlideGenerator
import math

class CurveCWGen(SlideGenerator):
    def __init__(self, verts: list[Location]):
        start_rot = self.get_rotation(verts[0])
        end_rot = self.get_rotation(verts[1])

        self.tangent_in_rot = start_rot + trig.get_tangent_angle_delta(self.CurveRadius, self.RingRadius, True)
        tangent_out_rot = end_rot + trig.get_tangent_angle_delta(self.CurveRadius, self.RingRadius, False)

        self.start_point = self.get_position_radial(start_rot)
        self.tangent_in_point = self.get_position_radial(self.tangent_in_rot, self.CurveRadius)
        self.tangent_out_point = self.get_position_radial(tangent_out_rot, self.CurveRadius)
        self.end_point = self.get_position_radial(end_rot)

        start_segment = trig.vec_sub(self.tangent_in_point, self.start_point)
        self.start_length = trig.vec_mag(start_segment)
        self.start_forward = math.atan2(start_segment[1], start_segment[0])

        self.curve_length = trig.get_angle_span(self.tangent_in_rot, tangent_out_rot, True) * self.CurveRadius

        end_segment = trig.vec_sub(self.end_point, self.tangent_out_point)
        end_len = trig.vec_mag(end_segment)
        self.end_forward = math.atan2(end_segment[1], end_segment[0])

        self.total_length = self.start_length + self.curve_length + end_len
    
    def get_point(self, time: float):
        distance_from_start = time * self.total_length
        pos = None
        rot = None
        if distance_from_start < self.start_length:
            scale = trig.inverse_lerp(0, self.start_length, distance_from_start)
            pos = trig.vec_lerp(self.start_point, self.tangent_in_point, scale)
            rot = self.start_forward
        
        elif distance_from_start < (self.start_length + self.curve_length):
            local_t = trig.inverse_lerp(self.start_length, self.start_length + self.curve_length, distance_from_start)
            x = math.cos(self.tangent_in_rot - self.curve_length / self.CurveRadius * local_t) * self.CurveRadius
            y = math.sin(self.tangent_in_rot - self.curve_length / self.CurveRadius * local_t) * self.CurveRadius
            pos = (x, y)
            forward = trig.vec_rotate(pos, -trig.TAU / 4)
            rot = math.atan2(forward[1], forward[0])
        
        else:
            scale = trig.inverse_lerp(self.start_length + self.curve_length, self.total_length, distance_from_start)
            pos = trig.vec_lerp(self.tangent_out_point, self.end_point, scale)
            rot = self.end_forward

        return pos, rot