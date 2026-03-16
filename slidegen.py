from slidegenerators.straight_line_gen import StraightLineGen
from slidegenerators.ring_cw_gen import RingCWGen
from slidegenerators.ring_ccw_gen import RingCCWGen
from slidegenerators.fold_gen import FoldGen
from slidegenerators.curve_cw_gen import CurveCWGen
from slidegenerators.curve_ccw_gen import CurveCCWGen
from slidegenerators.zig_zag_s_gen import ZigZagSGen
from slidegenerators.zig_zag_z_gen import ZigZagZGen
from slidegenerators.edge_fold_gen import EdgeFoldGen
from slidegenerators.edge_curve_ccw_gen import EdgeCurveCCWGen
from slidegenerators.edge_curve_cw_gen import EdgeCurveCWGen

def get_generator(id):
    match id:
        case 0:
            return StraightLineGen
        case 1:
            return RingCWGen
        case 2:
            return RingCCWGen
        case 3:
            return FoldGen
        case 4:
            return CurveCWGen
        case 5:
            return CurveCCWGen
        case 6:
            return ZigZagSGen
        case 7:
            return ZigZagZGen
        case 8:
            return EdgeFoldGen
        case 9:
            return EdgeCurveCWGen
        case 10:
            return EdgeCurveCCWGen
        case _:
            raise ValueError("invalid slide type id: " + str(id))