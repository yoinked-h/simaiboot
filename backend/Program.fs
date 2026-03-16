open SimaiSharp
open SimaiSharp.Structures
open SimaiSharp.Internal.SyntacticAnalysis
open System.IO
open System.Text.Json
open System.Collections.Generic

// --- Mappers for existing mode (Simai -> JSON) ---

let mapNote (n: Note) =
    {| location = n.location
       styles = n.styles
       appearance = n.appearance
       ``type`` = n.``type``
       length = n.length
       slideMorph = n.slideMorph
       slidePaths = n.slidePaths |}

let mapNoteCollection (nc: NoteCollection) =
    {| time = nc.time
       eachStyle = nc.eachStyle
       notes = nc |> Seq.map mapNote |> Seq.toArray |}


type SlideSegmentDto =
    { vertices: Location list
      slideType: SlideType }

type SlidePathDto =
    { startLocation: Location
      segments: SlideSegmentDto list
      delay: float32
      duration: float32
      ``type``: NoteType }

type NoteDto =
    { location: Location
      styles: NoteStyles
      appearance: NoteAppearance
      ``type``: NoteType
      length: float32 option
      slideMorph: SlideMorph
      slidePaths: SlidePathDto list }

type NoteCollectionDto =
    { time: float32
      eachStyle: EachStyle
      notes: NoteDto[] }

type ChartDto =
    { finishTiming: float32 option
      noteCollections: NoteCollectionDto[]
      timingChanges: TimingChange[] }


let mapToSlideSegment (dto: SlideSegmentDto) =
    let seg = SlideSegment(ResizeArray(dto.vertices))
    seg.slideType <- dto.slideType
    seg

let mapToSlidePath (dto: SlidePathDto) =
    let segments = dto.segments |> List.map mapToSlideSegment |> ResizeArray
    let sp = SlidePath(segments)
    sp.startLocation <- dto.startLocation
    sp.delay <- dto.delay
    sp.duration <- dto.duration
    sp.``type`` <- dto.``type``
    sp

let mapToNote (parent: NoteCollection) (dto: NoteDto) =
    let n = Note(parent)
    n.location <- dto.location
    n.styles <- dto.styles
    n.appearance <- dto.appearance
    n.``type`` <- dto.``type``
    n.length <- Option.toNullable dto.length
    n.slideMorph <- dto.slideMorph

    dto.slidePaths
    |> List.iter (fun spDto -> n.slidePaths.Add(mapToSlidePath spDto))

    n

let mapToNoteCollection (dto: NoteCollectionDto) =
    let nc = NoteCollection(dto.time)
    nc.eachStyle <- dto.eachStyle
    dto.notes |> Array.iter (fun nDto -> nc.Add(mapToNote nc nDto))
    nc

let mapToMaiChart (dto: ChartDto) =
    let chart = MaiChart()
    // Use reflection because properties might be internal set in the referenced assembly
    let setProp (name: string) (value: obj) =
        let prop = chart.GetType().GetProperty(name)

        if prop <> null then
            prop.SetValue(chart, value)

    setProp "FinishTiming" (Option.toNullable dto.finishTiming)
    setProp "TimingChanges" dto.timingChanges

    let noteCollections = dto.noteCollections |> Array.map mapToNoteCollection
    setProp "NoteCollections" noteCollections
    chart

[<EntryPoint>]
let main argv =
    let options = JsonSerializerOptions()
    options.IncludeFields <- true

    if argv.Length > 0 && (argv.[0] = "serialize" || argv.[0] = "-s") then
        // Serialize Mode: JSON File -> Simai String
        if argv.Length < 2 then
            printfn "Usage: Program.exe serialize <json_file>"
            1
        else
            let jsonPath = argv.[1]
            let json = File.ReadAllText(jsonPath)

            try
                let chartDto = JsonSerializer.Deserialize<ChartDto>(json, options)
                let chart = mapToMaiChart chartDto
                let simai = SimaiConvert.Serialize(chart)
                printfn "%s" simai
                0
            with ex ->
                printfn "Error deserializing JSON: %s" ex.Message
                1
    else if
        // Deserialize Mode: Simai File -> JSON
        argv.Length < 2
    then
        printfn "Usage: Program.exe <simai_file> <difficulty_index> OR Program.exe serialize <json_file>"
        1
    else
        let path = FileInfo(argv.[0])
        let simaiFile = new SimaiFile(path)
        let raw_text = simaiFile.GetValue($"inote_{argv.[1]}")
        let chart = SimaiConvert.Deserialize(raw_text)

        let chartDto =
            {| finishTiming = chart.FinishTiming
               noteCollections = chart.NoteCollections |> Array.map mapNoteCollection
               timingChanges = chart.TimingChanges |}

        let json = JsonSerializer.Serialize(chartDto, options)
        printfn "%s" json
        0
