import trig
from trig import VECTOR_TWO, Location, SlideGenerator
import math


class StraightLineGen(SlideGenerator):
    def __init__(self, verts: list[Location]):
        self.start_point = self.get_position(verts[0])
        self.end_point = self.get_position(verts[1])

        segment = trig.vec_sub(self.end_point, self.start_point)
        self.total_len = trig.vec_mag(segment)
        self.rotation = math.atan2(segment[1], segment[0])
        
    def get_point(self, time: float):
        pos = trig.vec_lerp(self.start_point, self.end_point, time)
        rot = self.rotation
        return pos, rot