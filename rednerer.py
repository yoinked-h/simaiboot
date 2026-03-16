import bisect
import json
import math
from pathlib import Path

import pyglet
from pyglet import gl

# pyglet.options['headless'] = True
from slidegen import get_generator
from simaisharpwrapper.wrapper import SimaisharpWrapper
from simaisharpwrapper.chart import Chart
import trig


def HEXTOTUPLE(h) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


gl.glClearColor(0, 0, 0, 1)
RES = 350
HRES = RES // 2
HEIGHT, WIDTH = RES, RES
COLORS = {
    "note": HEXTOTUPLE("FF62C1"),
    "each": HEXTOTUPLE("FFE100"),
    "slide": HEXTOTUPLE("06CDFB"),
    "touch": HEXTOTUPLE("5CDCF8"),
    "break": HEXTOTUPLE("E16005"),
    "holdline": HEXTOTUPLE("73FC66")
}

wrapper = SimaisharpWrapper()
data = Path('maidata.txt').read_text(encoding='utf-8')
test_chart = wrapper.deserialize(data, chart_key=6, convert_to_obj=True)

if not isinstance(test_chart, Chart):
    raise Exception("failed to deserialize chart")
malformat = json.loads(Path('nodes_boundingbox.json').read_text(encoding='utf-8'))


def fix(malformatted):
    fixed = {}
    for el in malformatted['zones']:
        el['center'] = (el['center'][0], 1 - el['center'][1])
        fixed[el['code']] = el
    return fixed

JSONDAT = fix(malformat)

window = pyglet.window.Window(RES, RES)

NOTE_SPEED = 1.5
TOUCH_BASE_SEPARATION = 15
TOUCH_HOLD_ARC_STEPS = 32
SLIDE_STEP_SIZE = 0.05
TIME_FROM_SPAWN_TO_RING = 1 / NOTE_SPEED # ms
GROW_PERCENTAGE = 0.5
PLAY_AREA_RADIUS = 150
TOUCH_HOLD_RADIUS = 25
CIRCLE_RADIUS = 12
CIRCLE_THICKNESS = 3
HOLD_LINE_WIDTH = 5
SLIDE_ARROW_LEN = 12
SLIDE_ARROW_THICK = 6
CENTER = (HRES, HRES)
# CENTER = (0,0)
# PLAY_AREA_RADIUS = 1
GOAL_POSITIONS = [
    trig.vec_add((PLAY_AREA_RADIUS * math.cos(2 * (i / 8) * math.pi + (math.pi / 8)),
                  PLAY_AREA_RADIUS * math.sin(2 * (i / 8) * math.pi + (math.pi / 8))), CENTER)
    for i in range(8)
]

def get_touch_note_loc(note):
    key = f"{'xabcde'[note.location.group]}{note.location.index+1}"
    cen = JSONDAT[key]['center'] #0-1
    loc = trig.vec_mul(cen, PLAY_AREA_RADIUS*2)
    loc = trig.vec_add(loc, ((RES - PLAY_AREA_RADIUS*2)/2, (RES - PLAY_AREA_RADIUS*2)/2))
    return loc

GOAL_POSITIONS = GOAL_POSITIONS[::-1]
GOAL_POSITIONS = GOAL_POSITIONS[6:] + GOAL_POSITIONS[:6]


def get_note_visual_state(time: float, hit_time: float, goal_pos: tuple[float, float], visible_until: float, keep_at_center_before_spawn: bool = False):
    spawn_time = hit_time - TIME_FROM_SPAWN_TO_RING
    if time > visible_until:
        return None
    startloc = trig.vec_lerp(CENTER, goal_pos, 0.2)
    if time < spawn_time:
        if not keep_at_center_before_spawn:
            return None
        return startloc, CIRCLE_RADIUS

    time_to_goal = hit_time - time
    percent = 1 - (time_to_goal / TIME_FROM_SPAWN_TO_RING)
    if percent < GROW_PERCENTAGE:
        radius = CIRCLE_RADIUS * (1 + ((percent - GROW_PERCENTAGE) / (1 - GROW_PERCENTAGE)))
        pos = startloc
    else:
        adjusted_percent = (percent - GROW_PERCENTAGE) / (1 - GROW_PERCENTAGE)
        radius = CIRCLE_RADIUS
        pos = trig.vec_lerp(startloc, goal_pos, adjusted_percent)

    if time >= hit_time:
        return goal_pos, CIRCLE_RADIUS

    return pos, radius


def hue_rotate(color: tuple[int, int, int, int], angle: float) -> tuple[int, int, int, int]:
    if len(color) == 3:
        color = (color[0], color[1], color[2], 255)
    r, g, b, a = color
    angle_rad = math.radians(angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    r_new = r * (cos_a + (1 - cos_a) / 3) + g * ((1 - cos_a) / 3 - sin_a / math.sqrt(3)) + b * ((1 - cos_a) / 3 + sin_a / math.sqrt(3))
    g_new = r * ((1 - cos_a) / 3 + sin_a / math.sqrt(3)) + g * (cos_a + (1 - cos_a) / 3) + b * ((1 - cos_a) / 3 - sin_a / math.sqrt(3))
    b_new = r * ((1 - cos_a) / 3 - sin_a / math.sqrt(3)) + g * ((1 - cos_a) / 3 + sin_a / math.sqrt(3)) + b * (cos_a + (1 - cos_a) / 3)

    return int(r_new), int(g_new), int(b_new), a

def get_note_color(note, noteset):
    if note.type == 4:
        return COLORS["break"]
    if noteset.is_each:
        return COLORS["each"]
    if note.type == 3 or len(note.slide_path) > 0:
        return COLORS["slide"]
    if note.type == 1:
        return COLORS["touch"]
    return COLORS["note"]


def set_alpha_color(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (color[0], color[1], color[2], int(alpha * 255))

def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _get_generator_length(generator_obj) -> float:
    if hasattr(generator_obj, "total_len"):
        return max(float(generator_obj.total_len), 0.0)
    if hasattr(generator_obj, "total_length"):
        return max(float(generator_obj.total_length), 0.0)
    if hasattr(generator_obj, "get_length"):
        return max(float(generator_obj.get_length()), 0.0)
    return 0.0


def _build_slide_segment_data(slide_path):
    segment_data = []
    total_length = 0.0
    for segment in slide_path.segments:
        if segment.slide_type == 11:
            # Fan notes are rendered as three straight paths:
            # end lane -1, end lane, end lane +1.
            base_vertices = list(segment.vertices)
            end_location = base_vertices[-1]
            fan_generators = []
            fan_lengths = []
            for index_offset in (-1, 0, 1):
                fan_vertices = list(base_vertices)
                fan_vertices[-1] = trig.Location((end_location.index + index_offset) % 8, end_location.group)
                fan_generator = get_generator(0)(fan_vertices)
                fan_generators.append(fan_generator)
                fan_lengths.append(_get_generator_length(fan_generator))

            center_length = fan_lengths[1] if len(fan_lengths) > 1 else 0.0
            segment_data.append((fan_generators, center_length))
            total_length += center_length
            continue
        generator = get_generator(segment.slide_type)(segment.vertices)
        # print(f"verts: {segment.vertices}, type: {segment.slide_type}, generator: {generator}")
        length = _get_generator_length(generator)
        segment_data.append((generator, length))
        total_length += length
    return segment_data, total_length


def _sample_slide_path(segment_data, total_length: float, t: float):
    if len(segment_data) == 0:
        return None

    def _sample_generators(generators, local_t: float):
        if isinstance(generators, list):
            return [generator.get_point(local_t) for generator in generators]
        return [generators.get_point(local_t)]

    t = _clamp01(t)
    if total_length <= 0:
        return _sample_generators(segment_data[-1][0], t)

    target_len = t * total_length
    traversed = 0.0
    for generator, segment_len in segment_data:
        next_traversed = traversed + segment_len
        if target_len <= next_traversed or segment_len <= 0:
            local_t = 0.0 if segment_len <= 0 else (target_len - traversed) / segment_len
            return _sample_generators(generator, _clamp01(local_t))
        traversed = next_traversed

    return _sample_generators(segment_data[-1][0], 1.0)


def _draw_slide_triangle(memory, batch, pos: tuple[float, float], rot: float, color="slide", alpha=1.0):
    tip = trig.vec_add(pos, trig.vec_mul((math.cos(rot), math.sin(rot)), SLIDE_ARROW_LEN))
    left = trig.vec_add(pos, trig.vec_mul((math.cos(rot + math.pi * 0.75), math.sin(rot + math.pi * 0.75)), SLIDE_ARROW_THICK))
    right = trig.vec_add(pos, trig.vec_mul((math.cos(rot - math.pi * 0.75), math.sin(rot - math.pi * 0.75)), SLIDE_ARROW_THICK))
    memory.append(
        pyglet.shapes.Triangle(
            tip[0],
            tip[1],
            left[0],
            left[1],
            right[0],
            right[1],
            color=set_alpha_color(COLORS[color], alpha),
            batch=batch,
        )
    )

def render(time, chart: Chart, window=window):
    window.switch_to()
    window.clear()
    batch = pyglet.graphics.Batch()
    memory = []
    memory.append(pyglet.shapes.Rectangle(0, 0, RES, RES, color=(0, 0, 0, 255), batch=batch))
    chart_list = sorted(chart, key=lambda ns: ns.time)
    chart_times = [ns.time for ns in chart_list]
    for g_pos in GOAL_POSITIONS:
        memory.append(pyglet.shapes.Circle(g_pos[0], g_pos[1], 5, color=(255, 255, 255, 255), batch=batch))
    end_idx = bisect.bisect_right(chart_times, time + TIME_FROM_SPAWN_TO_RING)
    for noteset in chart_list[:end_idx]:
        for note in noteset:
            hold_end_time = noteset.time + note.length
            if len(note.slide_path) > 0:
                for slp in note.slide_path:
                    hold_end_time += slp.delay + slp.duration
            if time > hold_end_time:
                continue

            g_pos = GOAL_POSITIONS[note.location.index]
            color = get_note_color(note, noteset)
            if note.type == 1 or (note.type == 2 and note.location.group != 0): #touch
                tloc = get_touch_note_loc(note)
                time_to_goal = noteset.time - time
                tpercent = 1-(time_to_goal / TIME_FROM_SPAWN_TO_RING)
                percent = (max(tpercent - 0.5, 0)*2) ** 2
                if percent > 1:
                    percent = 1
                if note.length > 0:
                    # Calculate hold progress for fill circle
                    hold_duration = hold_end_time - noteset.time
                    hold_progress = max(0, min(1, (time - noteset.time) / hold_duration)) if hold_duration > 0 else 0
                    
                    circle_radius = TOUCH_HOLD_RADIUS
                    memory.append(pyglet.shapes.Circle(tloc[0], tloc[1], circle_radius, color=(50, 50, 50), batch=batch))
                    
                    # Draw fill circle clockwise (starting from top, -90 degrees)
                    if hold_progress > 0:
                        # Create arc by drawing many small lines in a circle
                        arc_steps = max(1, int(hold_progress * TOUCH_HOLD_ARC_STEPS))
                        for step in range(arc_steps):
                            angle1 = -math.pi / 2 + (step / TOUCH_HOLD_ARC_STEPS) * 2 * math.pi
                            angle2 = -math.pi / 2 + ((step + 1) / TOUCH_HOLD_ARC_STEPS) * 2 * math.pi
                            
                            x1 = tloc[0] + circle_radius * math.cos(angle1)
                            y1 = tloc[1] + circle_radius * math.sin(angle1)
                            x2 = tloc[0] + circle_radius * math.cos(angle2)
                            y2 = tloc[1] + circle_radius * math.sin(angle2)
                            
                            memory.append(
                                pyglet.shapes.Line(
                                    x1, y1, x2, y2,
                                    color=(255,255,255,255),
                                    thickness=2,
                                    batch=batch,
                                )
                            )
                
                for edge_idx in range(4):
                    if note.length > 0:
                        color = hue_rotate((255, 128, 128), edge_idx * 90) #type: ignore
                    angle = (edge_idx / 4) * math.pi * 2 # up, right, down, left
                    offset = (math.cos(angle) * TOUCH_BASE_SEPARATION, math.sin(angle) * TOUCH_BASE_SEPARATION)

                    # Interpolate tip from spawn position to tloc based on percent
                    tip = trig.vec_lerp(trig.vec_add(tloc, offset), tloc, percent)
                    
                    # Base vertices perpendicular to offset direction
                    perp_angle = angle + math.pi / 2
                    perp_offset = (math.cos(perp_angle) * TOUCH_BASE_SEPARATION, math.sin(perp_angle) * TOUCH_BASE_SEPARATION)
                    left_base = trig.vec_add(tip, trig.vec_add(offset, perp_offset))
                    right_base = trig.vec_add(tip, trig.vec_sub(offset, perp_offset))
                    if percent == 0:
                        color= set_alpha_color(color, tpercent*2) #type: ignore
                    # Draw triangle lines
                    memory.append(
                        pyglet.shapes.Line(
                            tip[0],
                            tip[1],
                            left_base[0],
                            left_base[1],
                            color=color,
                            thickness=2,
                            batch=batch,
                        )
                    )
                    memory.append(
                        pyglet.shapes.Line(
                            tip[0],
                            tip[1],
                            right_base[0],
                            right_base[1],
                            color=color,
                            thickness=2,
                            batch=batch,
                        )
                    )
                    
                    memory.append(
                        pyglet.shapes.Line(
                            left_base[0],
                            left_base[1],
                            right_base[0],
                            right_base[1],
                            color=color,
                            thickness=2,
                            batch=batch,
                        )
                    )
                continue
                
            if note.type == 2 and note.location.group == 0: #hold
                start_state = get_note_visual_state(time, noteset.time, g_pos, hold_end_time)
                end_state = get_note_visual_state(time, hold_end_time, g_pos, hold_end_time, keep_at_center_before_spawn=True)
                if start_state is None or end_state is None:
                    continue
                start_pos, start_radius = start_state
                end_pos, end_radius = end_state
                memory.append(
                    pyglet.shapes.Line(
                        start_pos[0],
                        start_pos[1],
                        end_pos[0],
                        end_pos[1],
                        thickness=HOLD_LINE_WIDTH,
                        color=COLORS["holdline"],
                        batch=batch,
                    )
                )
                memory.append(pyglet.shapes.Circle(start_pos[0], start_pos[1], start_radius, color=color, batch=batch))
                should_render_end_circle = hold_end_time - time < TIME_FROM_SPAWN_TO_RING
                if should_render_end_circle:
                    memory.append(pyglet.shapes.Circle(end_pos[0], end_pos[1], end_radius, color=color, batch=batch))
                continue
            if note.type == 3 or len(note.slide_path) > 0: #slide
                note_state = get_note_visual_state(time, noteset.time, g_pos, hold_end_time)
                if note_state is not None and time < noteset.time:
                    pos, radius = note_state
                    memory.append(pyglet.shapes.Circle(pos[0], pos[1], radius, color=color, batch=batch))

                elapsed_since_hit = time - noteset.time
                for slide_path in note.slide_path:
                    segment_data, total_length = _build_slide_segment_data(slide_path)
                    if len(segment_data) == 0:
                        continue

                    if elapsed_since_hit < 0:
                        passed_t = -1.0
                    elif elapsed_since_hit < slide_path.delay:
                        passed_t = 0.0
                    elif slide_path.duration <= 0:
                        passed_t = 1.0
                    else:
                        passed_t = _clamp01((elapsed_since_hit - slide_path.delay) / slide_path.duration)
                    percentage_of_way_to_ring = min(((1+ elapsed_since_hit)/2) / TIME_FROM_SPAWN_TO_RING, 1.0)
                    arrow_t = max(0.0, SLIDE_STEP_SIZE)
                    while arrow_t <= 1.0 + 1e-6:
                        if arrow_t > passed_t + 1e-6:
                            sample = _sample_slide_path(segment_data, total_length, min(arrow_t, 1.0))
                            if sample is not None:
                                cname = "slide"
                                if slide_path.type == 4:
                                    cname = "break"
                                elif noteset.is_each:
                                    cname = "each"
                                for sample_pos, sample_rot in sample:
                                    world_pos = trig.vec_add(sample_pos, CENTER)
                                    _draw_slide_triangle(memory, batch, world_pos, sample_rot, color=cname, alpha=percentage_of_way_to_ring)
                        arrow_t += SLIDE_STEP_SIZE

                    if elapsed_since_hit >= 0:
                        sample = _sample_slide_path(segment_data, total_length, passed_t)
                        if sample is not None:
                            for sample_pos, _ in sample:
                                world_pos = trig.vec_add(sample_pos, CENTER)
                                memory.append(
                                    pyglet.shapes.Circle(
                                        world_pos[0],
                                        world_pos[1],
                                        CIRCLE_RADIUS,
                                        color=COLORS["slide"],
                                        batch=batch,
                                    )
                                )
                continue

            note_state = get_note_visual_state(time, noteset.time, g_pos, noteset.time)
            if note_state is None:
                continue
            pos, radius = note_state
            memory.append(pyglet.shapes.Circle(pos[0], pos[1], radius, color=color, batch=batch))
    batch.draw()
    
    window.flip()
    
    return pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()


if __name__ == "__main__":
    endtime = test_chart.finish_timing
    imgs = []
    for i in range(0, int(endtime * 60)):
        imgs.append(render(i/60, test_chart))
    import numpy as np
    def np_ify(img):
        # np.frombuffer(img.get_data(), dtype=np.uint8).reshape(img.height, img.width, 4) is flipped vertically, so we need to flip it back
        return np.flipud(np.frombuffer(img.get_data(), dtype=np.uint8).reshape(img.height, img.width, 4))
    import imageio
    npimgs = [np_ify(img) for img in imgs]
    imageio.mimwrite('output.mp4', npimgs, fps=60) # type: ignore