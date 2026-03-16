from typing import List, Optional
from enum import Enum

class Each_Style(Enum):
	Default = 0,
	ForceBroken = 1,
	ForceEach = 2

class Note_Group(Enum):
    Tap = 0,
    AGroup = 1,
    BGroup = 2,
    CGroup = 3,
    DGroup = 4,
    EGroup = 5

class Note_Type(Enum):
	Tap = 0,
	Touch = 1,
	Hold = 2,
	Slide = 3,
	Break = 4,
	ForceInvalidate = 5

class Appearance(Enum):
	Default = 0,
	ForceNormal = 1,
	ForceStar = 2,
	ForceStarSpinning = 3

class Slide_Morph(Enum):
    FadeIn = 0,
    SuddenIn = 1

class Slide_Type(Enum):
	StraightLine = 0,
	RingCw = 1,
	RingCcw = 2,
	Fold = 3,
	CurveCw = 4,
	CurveCcw = 5,
	ZigZagS = 6,
	ZigZagZ = 7,
	EdgeFold = 8,
	EdgeCurveCw = 9,
	EdgeCurveCcw = 10,
	Fan = 11,

class Location:
    def __init__(self, index: int, group: int):
        self.index = index
        self.group = group
    def __repr__(self):
        return f"Location(index={self.index}, group={self.group})"

class Slide_Segment:
    def __init__(self, vertices: List[Location], slide_type: int):
        self.vertices = vertices
        self.slide_type = slide_type

class Slide_Path:
    def __init__(self, start_location: Location, segments: List[Slide_Segment], delay: float, duration: float, type: int):
        self.start_location = start_location
        self.segments = segments
        self.delay = delay
        self.duration = duration
        self.type = type

class Note:
    def __init__(self, location: Location, appearance: int, type: int, length: Optional[float], slide_morph: int, slide_path: List[Slide_Path], style: int):
        self.location = location
        self.appearance = appearance
        self.type = type
        self.length = length if length is not None else 0
        self.slide_morph = slide_morph
        self.slide_path = slide_path
        self.style = style

class TimingChange:
    def __init__(self, time: float, tempo: float, subdivisions: float):
        self.time = time
        self.tempo = tempo
        self.subdivisions = subdivisions

class NoteCollection:
    def __init__(self, time: float, each_style: int, notes: List[Note]):
        self.time = time
        self.each_style = each_style
        self.notes = notes
        self.is_each = ((len(notes) > 1 and each_style == 0) or (each_style == 2)) and not (each_style == 1)
    
    def __iter__(self):
        return iter(self.notes)
    
    def __len__(self):
        return len(self.notes)
    
    def __getitem__(self, index):
        return self.notes[index]
        
class Chart:
    def __init__(self, finish_timing: float, note_collection: List[NoteCollection], timing_changes: List[TimingChange]):
        self.finish_timing = finish_timing
        self.note_collection = note_collection
        self.timing_changes = timing_changes
    
    def __iter__(self):
        return iter(self.note_collection)
    
    def __len__(self):
        return len(self.note_collection)
    
    def __getitem__(self, index):
        return self.note_collection[index]

def convert(data: dict) -> Chart:
    timing_changes = []
    for tc_data in data.get('timingChanges', []):
        timing_change = TimingChange(
            time=tc_data['time'],
            tempo=tc_data['tempo'],
            subdivisions=tc_data['subdivisions']
        )
        timing_changes.append(timing_change)
    
    note_collections = []
    for nc_data in data.get('noteCollections', []):
        notes = []
        for note_data in nc_data.get('notes', []):
            location = Location(
                index=note_data['location']['index'],
                group=note_data['location']['group']
            )
            
            slide_paths = []
            for sp_data in note_data.get('slidePaths', []):
                start_location = Location(
                    index=sp_data['startLocation']['index'],
                    group=sp_data['startLocation']['group']
                )
                
                segments = []
                lastpos = location
                for seg_data in sp_data.get('segments', []):
                    vertices = [
                        Location(
                            index=v['index'],
                            group=v['group']
                        )
                        for v in seg_data.get('vertices', [])
                    ]
                    vertices.insert(0, lastpos) # workaround...
                    segment = Slide_Segment(
                        vertices=vertices,
                        slide_type=seg_data['slideType']
                    )
                    lastpos = vertices[-1]
                    segments.append(segment)
                
                slide_path = Slide_Path(
                    start_location=start_location,
                    segments=segments,
                    delay=sp_data['delay'],
                    duration=sp_data['duration'],
                    type=sp_data['type']
                )
                slide_paths.append(slide_path)
            
            note = Note(
                location=location,
                appearance=note_data['appearance'],
                type=note_data['type'],
                length=note_data.get('length'),
                slide_morph=note_data['slideMorph'],
                slide_path=slide_paths,
                style=note_data.get('style', 0)
            )
            notes.append(note)
        
        note_collection = NoteCollection(
            time=nc_data['time'],
            each_style=nc_data['eachStyle'],
            notes=notes
        )
        note_collections.append(note_collection)
    
    chart = Chart(
        finish_timing=data['finishTiming'],
        note_collection=note_collections,
        timing_changes=timing_changes
    )
    return chart

if __name__ == "__main__":
    import json
    with open("ref.json", "r") as f:
        data = json.load(f)
    chart = convert(data)
    print(chart)