import trig
from trig import VECTOR_TWO, Location, SlideGenerator
import math


class ZigZagSGen(SlideGenerator):
    def __init__(self, verts: list[Location]):
        dist = self.PlayfieldRadius
        inner = self.CenterRadius
        start_rot = self.get_rotation(verts[0])
        end_rot = self.get_rotation(verts[1])

        start_zag = start_rot + trig.TAU / 4
        end_zag = end_rot + trig.TAU / 4

        self.start_point = (dist * math.cos(start_rot), dist * math.sin(start_rot))

        self.start_zag_point = (inner * math.cos(start_zag), inner * math.sin(start_zag))

        start_segment = trig.vec_sub(self.start_zag_point, self.start_point)
        self.start_segment_len = trig.vec_mag(start_segment)
        self.start_rot = math.atan2(start_segment[1], start_segment[0])

        self.end_zag_point = (inner * math.cos(end_zag), inner * math.sin(end_zag))

        mid_segment = trig.vec_sub(self.end_zag_point, self.start_zag_point)
        self.mid_segment_len = trig.vec_mag(mid_segment)
        self.mid_rot = math.atan2(mid_segment[1], mid_segment[0])

        self.end_point = (dist * math.cos(end_rot), dist * math.sin(end_rot))

        end_segment = trig.vec_sub(self.end_point, self.end_zag_point)
        end_segment_len = trig.vec_mag(end_segment)
        self.end_rot = math.atan2(end_segment[1], end_segment[0])

        self.total_len = self.start_segment_len + self.mid_segment_len + end_segment_len

    def get_point(self, time: float):
        dist = time * self.total_len

        if dist < self.start_segment_len:
            scale = trig.inverse_lerp(0, self.start_segment_len, dist)
            pos = trig.vec_lerp(self.start_point, self.start_zag_point, scale)
            rot = self.start_rot

        elif dist < self.start_segment_len + self.mid_segment_len:
            mid_len = self.start_segment_len + self.mid_segment_len
            scale = trig.inverse_lerp(self.start_segment_len, mid_len, dist)
            pos = trig.vec_lerp(self.start_zag_point, self.end_zag_point, scale)
            rot = self.mid_rot
        else:
            mid_len = self.start_segment_len + self.mid_segment_len
            scale = trig.inverse_lerp(mid_len, self.total_len, dist)
            pos = trig.vec_lerp(self.end_zag_point, self.end_point, scale)
            rot = self.end_rot

        return pos, rot