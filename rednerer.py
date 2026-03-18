import bisect
import json
import math
from pathlib import Path
from tqdm import tqdm
import pyglet
from pyglet import gl

pyglet.options['headless'] = True
from slidegen import get_generator
from simaisharpwrapper.wrapper import SimaisharpWrapper
from simaisharpwrapper.chart import Chart
import trig


def HEXTOTUPLE(h) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


#gl.glClearColor(0, 0, 0, 1)
RES = 350
HRES = RES // 2
HEIGHT, WIDTH = RES, RES
COLORS = {
    "note": HEXTOTUPLE("FF62C1"),
    "each": HEXTOTUPLE("FFE100"),
    "slide": HEXTOTUPLE("06CDFB"),
    "touch": HEXTOTUPLE("5CDCF8"),
    "break": HEXTOTUPLE("E16005"),
    "holdline": HEXTOTUPLE("73FC66"),
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

# NOTE_SPEED = 1.5
# TOUCH_BASE_SEPARATION = 15
# TOUCH_HOLD_ARC_STEPS = 32
# SLIDE_STEP_DISTANCE = 20.0
# TIME_FROM_SPAWN_TO_RING = 1 / NOTE_SPEED
# GROW_PERCENTAGE = 0.5
PLAY_AREA_RADIUS = 150
# TOUCH_HOLD_RADIUS = 25
# CIRCLE_RADIUS = 12
# HOLD_LINE_WIDTH = 5
# NOTE_LURCH = 0.2
# SLIDE_ARROW_LEN = 12
# SLIDE_ARROW_THICK = 10
# TOUCHSLIDE_ANGLE_SEP = math.radians(36)
const_settings = {
    "note_speed": 1.5,
    "touch_base_separation": 15,
    "touch_hold_arc_steps": 32,
    "slide_step_distance": 20.0,
    # add after
    "grow_percentage": 0.5,
    # play area is fixed
    "touch_hold_radius": 25,
    "circle_radius": 12,
    "hold_line_width": 5,
    "note_lurch": 0.2,
    "slide_arrow_len": 12,
    "slide_arrow_thick": 10,
    "touchslide_angle_sep": math.radians(36)
}
const_settings['time_from_spawn_to_ring'] = 1 / const_settings['note_speed']
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
    

def draw_sensors(memory, batch):
    for _, v in JSONDAT.items():
        verts = v['coordinates']
        for i in range(len(verts)):
            x1, y1 = verts[i] #0-1
            x2, y2 = verts[(i+1)%len(verts)]
            x1 = x1 * PLAY_AREA_RADIUS * 2 + (RES - PLAY_AREA_RADIUS*2)/2
            y1 = (1-y1) * PLAY_AREA_RADIUS * 2 + (RES - PLAY_AREA_RADIUS*2)/2
            x2 = x2 * PLAY_AREA_RADIUS * 2 + (RES - PLAY_AREA_RADIUS*2)/2
            y2 = (1-y2) * PLAY_AREA_RADIUS * 2 + (RES - PLAY_AREA_RADIUS*2)/2
            memory.append(
                pyglet.shapes.Line(
                    x1, y1, x2, y2,
                    color=(255,255,255,75),
                    thickness=1,
                    batch=batch,
                )
            )


def get_note_visual_state(time: float, hit_time: float, goal_pos: tuple[float, float], visible_until: float, keep_at_center_before_spawn: bool = False,
                          time_to_spawn=None, circle_rad=None, grow_percent=None, lurch=None):
    if time_to_spawn is None:
        time_to_spawn = const_settings['time_from_spawn_to_ring']
    if circle_rad is None:
        circle_rad = const_settings['circle_radius']
    if grow_percent is None:
        grow_percent = const_settings['grow_percentage']
    if lurch is None:
        lurch = const_settings['note_lurch']
    spawn_time = hit_time - time_to_spawn
    if time > visible_until:
        return None
    startloc = trig.vec_lerp(CENTER, goal_pos, lurch)
    if time < spawn_time:
        if not keep_at_center_before_spawn:
            return None
        return startloc, circle_rad

    time_to_goal = hit_time - time
    percent = 1 - (time_to_goal / time_to_spawn)
    if percent < grow_percent:
        radius = circle_rad * (1 + ((percent - grow_percent) / (1 - grow_percent)))
        pos = startloc
    else:
        adjusted_percent = (percent - grow_percent) / (1 - grow_percent)
        radius = circle_rad
        pos = trig.vec_lerp(startloc, goal_pos, adjusted_percent)

    if time >= hit_time:
        return goal_pos, circle_rad

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


def _get_slide_step_size(total_length: float, slidestep=None) -> float:
    if slidestep is None:
        slidestep = const_settings['slide_step_distance']
    if total_length <= 0:
        return 1.0
    return min(1.0, slidestep / total_length)


def _draw_slide_triangle(memory, batch, pos: tuple[float, float], rot: float, color="slide", alpha=1.0, arrow_thickness=None, arrow_len=None):
    if arrow_thickness is None:
        arrow_thickness = const_settings['slide_arrow_thick']
    if arrow_len is None:
        arrow_len = const_settings['slide_arrow_len']
    tip = trig.vec_add(pos, trig.vec_mul((math.cos(rot), math.sin(rot)), arrow_len))
    left = trig.vec_add(pos, trig.vec_mul((math.cos(rot + math.pi * 0.75), math.sin(rot + math.pi * 0.75)), arrow_thickness))
    right = trig.vec_add(pos, trig.vec_mul((math.cos(rot - math.pi * 0.75), math.sin(rot - math.pi * 0.75)), arrow_thickness))
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
def render(time, chart: Chart, overrides=None):
    window = pyglet.window.Window(RES, RES)
    if overrides is None:
        overrides = {}
    settings = const_settings.copy()
    settings.update(overrides)
    settings['time_from_spawn_to_ring'] = 1 / settings['note_speed']
    window.switch_to()
    window.clear()
    batch = pyglet.graphics.Batch()
    memory = []
    memory.append(pyglet.shapes.Rectangle(0, 0, RES, RES, color=(0, 0, 0, 255), batch=batch))
    chart_list = sorted(chart, key=lambda ns: ns.time)
    chart_times = [ns.time for ns in chart_list]
    draw_sensors(memory, batch)
    for g_pos in GOAL_POSITIONS:
        memory.append(pyglet.shapes.Circle(g_pos[0], g_pos[1], 5, color=(255, 255, 255, 255), batch=batch))
    end_idx = bisect.bisect_right(chart_times, time + settings['time_from_spawn_to_ring'])
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
            DO_TOUCH_SLIDE_EXCEPTION = False
            if (note.type == 1 or ((note.type == 2 or note.type == 3) and note.location.group != 0)) and (time <= (noteset.time + note.length)): #touch
                tloc = get_touch_note_loc(note)
                time_to_goal = noteset.time - time
                tpercent = 1-(time_to_goal / settings['time_from_spawn_to_ring'])
                percent = (max(tpercent - 0.5, 0)*2) ** 2
                if percent > 1:
                    percent = 1
                if note.length > 0:
                    # Calculate hold progress for fill circle
                    hold_duration = hold_end_time - noteset.time
                    hold_progress = max(0, min(1, (time - noteset.time) / hold_duration)) if hold_duration > 0 else 0
                    
                    circle_radius = settings['touch_hold_radius'] 
                    memory.append(pyglet.shapes.Circle(tloc[0], tloc[1], circle_radius, color=(255,255,255, 51), batch=batch))
                    
                    # Draw fill circle clockwise (starting from top, -90 degrees)
                    if hold_progress > 0:
                        # Create arc by drawing many small lines in a circle
                        arc_steps = max(1, int(hold_progress * settings['touch_hold_arc_steps']))
                        for step in range(arc_steps):
                            angle1 = -math.pi / 2 + (step / settings['touch_hold_arc_steps']) * 2 * math.pi
                            angle2 = -math.pi / 2 + ((step + 1) / settings['touch_hold_arc_steps']) * 2 * math.pi
                            
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
                    
                if len(note.slide_path) == 0:
                    for edge_idx in range(4):
                        if note.length > 0:
                            color = hue_rotate((255, 128, 128), edge_idx * 90) #type: ignore
                        angle = (edge_idx / 4) * math.pi * 2 # up, right, down, left
                        offset = (math.cos(angle) * settings['touch_base_separation'], math.sin(angle) * settings['touch_base_separation'])
                        # Interpolate tip from spawn position to tloc based on percent
                        tip = trig.vec_lerp(trig.vec_add(tloc, offset), tloc, percent)
                        # Base vertices perpendicular to offset direction
                        perp_angle = angle + math.pi / 2
                        perp_offset = (math.cos(perp_angle) * settings['touch_base_separation'], math.sin(perp_angle) * settings['touch_base_separation'])
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
                else:
                    # print("slide touch", note.slide_path)
                    DO_TOUCH_SLIDE_EXCEPTION = True
                    for edge_idx in range(5): # pentagon
                        angle = (edge_idx / 5) * math.pi * 2
                        offset = (math.cos(angle) * settings['touch_base_separation'], math.sin(angle) * settings['touch_base_separation'])
                        tip = trig.vec_lerp(trig.vec_add(tloc, offset), tloc, percent)
                        perp_angle = angle + math.pi / 2
                        perp_offset = (math.cos(perp_angle) * settings['touch_base_separation'], math.sin(perp_angle) * settings['touch_base_separation'])
                        # angled away by TOUCHSLIDE_ANGLE_SEP
                        left_base = trig.vec_add(tip, trig.vec_add(trig.vec_mul(offset, math.cos(settings['touchslide_angle_sep'])) , trig.vec_mul(perp_offset, math.sin(settings['touchslide_angle_sep']))))
                        right_base = trig.vec_add(tip, trig.vec_sub(trig.vec_mul(offset, math.cos(settings['touchslide_angle_sep'])) , trig.vec_mul(perp_offset, math.sin(settings['touchslide_angle_sep']))))
                        if percent == 0:
                            color= set_alpha_color(color, tpercent*2) #type: ignore
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
        
                    
                
            if note.type == 2 and note.location.group == 0 and not DO_TOUCH_SLIDE_EXCEPTION: #hold
                start_state = get_note_visual_state(time, noteset.time, g_pos, hold_end_time, time_to_spawn=settings['time_from_spawn_to_ring'], circle_rad=settings['circle_radius'], grow_percent=settings['grow_percentage'], lurch=settings['note_lurch'])
                end_state = get_note_visual_state(time, hold_end_time, g_pos, hold_end_time, keep_at_center_before_spawn=True, time_to_spawn=settings['time_from_spawn_to_ring'], circle_rad=settings['circle_radius'], grow_percent=settings['grow_percentage'], lurch=settings['note_lurch'])
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
                        thickness=settings['hold_line_width'],
                        color=COLORS["holdline"],
                        batch=batch,
                    )
                )
                memory.append(pyglet.shapes.Circle(start_pos[0], start_pos[1], start_radius, color=color, batch=batch))
                should_render_end_circle = hold_end_time - time < settings['time_from_spawn_to_ring']
                if should_render_end_circle:
                    memory.append(pyglet.shapes.Circle(end_pos[0], end_pos[1], end_radius, color=color, batch=batch))
                continue
            if note.type == 3 or len(note.slide_path) > 0: #slide
                note_state = get_note_visual_state(time, noteset.time, g_pos, hold_end_time, time_to_spawn=settings['time_from_spawn_to_ring'], circle_rad=settings['circle_radius'], grow_percent=settings['grow_percentage'], lurch=settings['note_lurch'])
                if note_state is not None and time < noteset.time and not DO_TOUCH_SLIDE_EXCEPTION:
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
                    percentage_of_way_to_ring = min(((1+ elapsed_since_hit)/2) / settings['time_from_spawn_to_ring'], 1.0)
                    step_size = _get_slide_step_size(total_length, slidestep=settings['slide_step_distance'])
                    arrow_t = max(0.0, step_size)
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
                                    _draw_slide_triangle(memory, batch, world_pos, sample_rot, color=cname, alpha=percentage_of_way_to_ring, arrow_thickness=settings['slide_arrow_thick'], arrow_len=settings['slide_arrow_len'])
                        arrow_t += step_size

                    if elapsed_since_hit >= 0:
                        sample = _sample_slide_path(segment_data, total_length, passed_t)
                        if sample is not None:
                            for sample_pos, _ in sample:
                                world_pos = trig.vec_add(sample_pos, CENTER)
                                memory.append(
                                    pyglet.shapes.Circle(
                                        world_pos[0],
                                        world_pos[1],
                                        settings['circle_radius'],
                                        color=COLORS["slide"],
                                        batch=batch,
                                    )
                                )
                continue

            note_state = get_note_visual_state(time, noteset.time, g_pos, noteset.time, time_to_spawn=settings['time_from_spawn_to_ring'], circle_rad=settings['circle_radius'], grow_percent=settings['grow_percentage'], lurch=settings['note_lurch'])
            if note_state is None:
                continue
            pos, radius = note_state
            memory.append(pyglet.shapes.Circle(pos[0], pos[1], radius, color=color, batch=batch))
    batch.draw()
    
    window.flip()
    
    return pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()




FPS = 30

def main(chtxt, overrides=None):
    data = r"&inote_6=(120){4},," + chtxt + ",(120){4},,E"
    test_chart = wrapper.deserialize(data, chart_key=6, convert_to_obj=True)

    if not isinstance(test_chart, Chart):
        raise Exception("failed to deserialize chart")
    endtime = test_chart.finish_timing
    imgs = []
    for i in tqdm(range(0, int(endtime * FPS))):
        imgs.append(render(i/FPS, test_chart, overrides=overrides))
    import numpy as np
    def np_ify(img):
        return np.flipud(np.frombuffer(img.get_data(), dtype=np.uint8).reshape(img.height, img.width, 4))
    import imageio
    npimgs = [np_ify(img) for img in imgs]
    imageio.mimwrite('output.mp4', npimgs, fps=FPS) # type: ignore
    return "output.mp4"

TX = "1,1,1,1,2,2,2,2,,,,,3,3,3,3"
# main(TX, overrides={"note_speed": 5})
# exit()

import asyncio
import discord, json
import os # default module
from dotenv import load_dotenv # type: ignore
from dataclasses import dataclass
from collections import deque
from itertools import count

load_dotenv() # load all the variables from the env file
bot = discord.Bot()


@dataclass
class RenderJob:
    job_id: int
    simai_data: tuple[str, dict] # (simai string, cparams dict)
    future: asyncio.Future


render_queue: asyncio.Queue[RenderJob] = asyncio.Queue()
render_worker_task: asyncio.Task | None = None
queued_job_ids: deque[int] = deque()
active_job_id: int | None = None
job_id_counter = count(1)


def get_job_position(job_id: int) -> tuple[int | None, bool]:
    if active_job_id == job_id:
        return 1, True

    for idx, queued_id in enumerate(queued_job_ids):
        if queued_id == job_id:
            base = 2 if active_job_id is not None else 1
            return base + idx, False

    return None, False


async def render_worker() -> None:
    global active_job_id
    while True:
        job = await render_queue.get()
        try:
            active_job_id = job.job_id
            if queued_job_ids and queued_job_ids[0] == job.job_id:
                queued_job_ids.popleft()
            result = await asyncio.to_thread(main, job.simai_data[0], overrides=job.simai_data[1])
            if not job.future.done():
                job.future.set_result(result)
        except Exception as exc:
            if not job.future.done():
                job.future.set_exception(exc)
        finally:
            if active_job_id == job.job_id:
                active_job_id = None
            render_queue.task_done()

@bot.event
async def on_ready():
    global render_worker_task
    if render_worker_task is None or render_worker_task.done():
        render_worker_task = asyncio.create_task(render_worker())
    print(f"{bot.user} ready")

@bot.slash_command(name="simai_render", description="pass raw simai, e.g. `7h[4:1]/1h[4:1],5,5,5,5,` defaults to 120 bpm and 4 subdiv")
async def simai_render(ctx: discord.ApplicationContext, simai_data: str, cparams: str = None):
    if cparams is None:
        cparams = r"{}"
    try:
        ovrds = json.loads(cparams)
    except json.JSONDecodeError:
        ovrds = False
    ovrd_msg = f"(with {len(ovrds)} custom parameters)" if ovrds else "(cparams failed)"
    job_id = next(job_id_counter)
    queued_job_ids.append(job_id)
    queue_position, _ = get_job_position(job_id)
    temp_embed = discord.Embed(
        title="render queue",
        description=f"maimai queue, position #{queue_position}",
        image="https://files.catbox.moe/6o59ey.gif",
        color=0xDA70D6,
    )
    await ctx.respond(embed=temp_embed)
    original_message = await ctx.interaction.original_response()
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    await render_queue.put(RenderJob(job_id=job_id, simai_data=(simai_data, ovrds), future=future))
    try:
        last_position = queue_position
        last_rendering_state = False
        while True:
            try:
                result = await asyncio.wait_for(asyncio.shield(future), timeout=1.5)
                break
            except TimeoutError:
                position, is_rendering = get_job_position(job_id)
                if position is None:
                    continue
                if position != last_position or is_rendering != last_rendering_state:
                    if is_rendering:
                        await original_message.edit(
                            embed=discord.Embed(
                                title="rendering now",
                                description=f"rendering now {ovrd_msg}",
                                image="https://files.catbox.moe/6o59ey.gif",
                                color=0xDA70D6,
                            )
                        )
                    else:
                        await original_message.edit(
                            embed=discord.Embed(
                                title="render queue",
                                description=f"maimai queue, position #{position} {ovrd_msg}",
                                image="https://files.catbox.moe/6o59ey.gif",
                                color=0xDA70D6,
                            )
                        )
                    last_position = position
                    last_rendering_state = is_rendering
        await original_message.edit(f"```\n{simai_data[:1985]}\n```", file=discord.File(result, filename="render.mp4"), embed=None)
    except Exception as e:
        print(e)
        if active_job_id != job_id:
            try:
                queued_job_ids.remove(job_id)
            except ValueError:
                pass
        await original_message.edit("something errored", embed=None)
    


bot.run(os.getenv("TOKEN"))
