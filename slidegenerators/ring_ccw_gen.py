import trig
from trig import VECTOR_TWO, Location, SlideGenerator
import math


class RingCCWGen(SlideGenerator):
    def __init__(self, verts: list[Location]):
        in_pos = self.get_position(verts[0])
        in_rads = trig.to_polar_ang(in_pos)

        out_pos = self.get_position(verts[1])
        out_rads = trig.to_polar_ang(out_pos)

        self.start_rot = in_rads

        self.angle_span = trig.get_angle_span(in_rads, out_rads, False)
        self.start_rad = self.get_radius_from_center(verts[0])
        self.end_rad = self.get_radius_from_center(verts[1])

        self.total_len = self.angle_span * (self.start_rad + self.end_rad) / 2

    def get_point(self, time: float):
        radius_at_t = trig.lerp(self.start_rad, self.end_rad, time)
        rot_at_t = self.start_rot + self.angle_span * time

        pos = (math.cos(rot_at_t) * radius_at_t, math.sin(rot_at_t) * radius_at_t)

        rot = rot_at_t + trig.TAU / 4

        return pos, rot