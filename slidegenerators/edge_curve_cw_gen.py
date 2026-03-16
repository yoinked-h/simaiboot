import trig
from trig import VECTOR_TWO, Location, SlideGenerator
import math


class EdgeCurveCWGen(SlideGenerator):
    CurveRadius = SlideGenerator.CenterRadius * 1.2
    CenterAngularOffset = trig.TAU / 4 - trig.TAU / 16
    CenterRadialOffset = SlideGenerator.PlayfieldRadius * 0.4662

    def __init__(self, verts: list[Location]):
        start_rot = self.get_rotation(verts[0])
        end_rot = self.get_rotation(verts[1])
        
        center_angle = start_rot + self.CenterAngularOffset
        self.center_pos = (self.CenterRadialOffset * math.cos(center_angle), self.CenterRadialOffset * math.sin(center_angle))
    
        self.start_point = self.get_position_radial(start_rot)

        rel_start_rot = trig.to_polar_ang(self.start_point, self.center_pos)

        magnitude = trig.vec_mag(trig.vec_sub(self.start_point, self.center_pos))
        start_delta = trig.get_tangent_angle_delta(self.CurveRadius, magnitude, True)

        self.tangent_in_rot = rel_start_rot + start_delta
        self.tangent_in_point = trig.vec_add(self.get_position_radial(self.tangent_in_rot, self.CurveRadius), self.center_pos)

        self.end_point = self.get_position_radial(end_rot)

        rel_end_rot = trig.to_polar_ang(self.end_point, self.center_pos)
        end_magnitude = trig.vec_mag(trig.vec_sub(self.end_point, self.center_pos))
        end_delta = trig.get_tangent_angle_delta(self.CurveRadius, end_magnitude, False)

        tangent_out_rot = rel_end_rot + end_delta
        self.tangent_out_point = trig.vec_add(self.get_position_radial(tangent_out_rot, self.CurveRadius), self.center_pos)
        
        start_segment = trig.vec_sub(self.tangent_in_point, self.start_point)
        self.start_len = trig.vec_mag(start_segment)
        self.start_rot = math.atan2(start_segment[1], start_segment[0])

        self.curve_len = trig.get_angle_span(self.tangent_in_rot, tangent_out_rot, True, trig.TAU / 4) * self.CurveRadius

        end_segment = trig.vec_sub(self.end_point, self.tangent_out_point)
        end_len = trig.vec_mag(end_segment)
        self.end_rot = math.atan2(end_segment[1], end_segment[0])

        self.total_len = self.start_len + self.curve_len + end_len

    def get_point(self, time: float):
        dist_from_start = time * self.total_len
        pos = None
        vec = None
        
        if dist_from_start < self.start_len:
            scale = trig.inverse_lerp(0, self.start_len, dist_from_start)
            pos = trig.vec_lerp(self.start_point, self.tangent_in_point, scale)
            rot = self.start_rot

        elif dist_from_start < self.start_len + self.curve_len:
            local_t = trig.inverse_lerp(self.start_len, self.start_len + self.curve_len, dist_from_start)
            x = self.CurveRadius * math.cos(self.tangent_in_rot - self.curve_len / self.CurveRadius * local_t)
            y = self.CurveRadius * math.sin(self.tangent_in_rot - self.curve_len / self.CurveRadius * local_t)
            pos = (x, y)
            forward = trig.vec_rotate(pos, -trig.TAU / 4)
            rot = math.atan2(forward[1], forward[0])
            pos = trig.vec_add(pos, self.center_pos)

        else:
            scale = trig.inverse_lerp(self.start_len + self.curve_len, self.total_len, dist_from_start)
            pos = trig.vec_lerp(self.tangent_out_point, self.end_point, scale)
            rot = self.end_rot

        return pos, rot