import trig
from ..trig import VECTOR_TWO, Location, SlideGenerator
import math


class EdgeFoldGen(SlideGenerator):
    def __init__(self, verts: list[Location]):
        self.start_point = self.get_position(verts[0])
        self.mid_point = self.get_position(verts[1])
        self.end_point = self.get_position(verts[2])

        start_seg = trig.vec_sub(self.mid_point, self.start_point)
        self.start_seg_len = trig.vec_mag(start_seg)
        self.start_rot = math.atan2(start_seg[1], start_seg[0])

        end_seg = trig.vec_sub(self.end_point, self.mid_point)
        end_seg_len = trig.vec_mag(end_seg)
        self.end_rot = math.atan2(end_seg[1], end_seg[0])

        self.total_len = self.start_seg_len + end_seg_len

    def get_point(self, time: float):
        dist = self.total_len * time
        pos = None
        rot = None

        if dist < self.start_seg_len:
            scale = trig.inverse_lerp(0, self.start_seg_len / self.total_len, time)
            pos = trig.vec_lerp(self.start_point, self.mid_point, scale)
            rot = self.start_rot
        else:
            scale = trig.inverse_lerp(self.start_seg_len / self.total_len, 1, time)
            pos = trig.vec_lerp(self.mid_point, self.end_point, scale)
            rot = self.end_rot

        return pos, rot