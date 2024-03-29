from pathlib import Path

from pytest import fixture
import guitarpro as gm
import music21 as m21

from src.loading.serialization import PyGuitarProSerializer
from src.transforming.guitarprotomusic21convertor import GuitarProToMusic21Convertor


@fixture
def gp_to_m21_convertor():
    test_folder_path = Path.home() / "GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    gp_file = gp_serializer.load(
        test_folder_path / "Antonio Carlos, Jobim - Engano.gp4.gp2tokens2gp.gp5"
    )
    gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
    return gp_to_m21_convertor


def test_guitarpro_to_music21_convertor_init(gp_to_m21_convertor):
    metadata = gp_to_m21_convertor.metadata
    assert type(gp_to_m21_convertor.gp_stream) == gm.models.Song
    assert type(metadata) == dict
    assert metadata["title"] == "Antonio Carlos, Jobim - Engano.gp4"
    assert metadata["artist"] == "Antonio Carlos, Jobim"
    assert metadata["tempo"] == 70


def test_create_new_m21_score(gp_to_m21_convertor):
    new_m21_score = gp_to_m21_convertor._create_new_m21_score()
    assert type(new_m21_score) == m21.stream.Score
    assert new_m21_score.metadata.title == "Antonio Carlos, Jobim - Engano"
    assert new_m21_score.metadata.composer == "Antonio Carlos, Jobim"


def test_create_new_m21_part(gp_to_m21_convertor):
    gp_song = gp_to_m21_convertor.gp_stream
    track = gp_song.tracks[0]
    instrument_id = track.channel.instrument  # Midi instrument id
    track_name = track.name
    is_percussion = track.isPercussionTrack
    assert type(gp_song) == gm.models.Song
    assert type(track) == gm.models.Track
    m21_part = gp_to_m21_convertor._create_m21_part(
        0, instrument_id, track_name, is_percussion
    )
    assert type(m21_part) == m21.stream.Part
    assert m21_part.getInstrument().instrumentName == "Electric Guitar"


def test_create_new_m21_measure(gp_to_m21_convertor):
    gp_song = gp_to_m21_convertor.gp_stream
    gp_measure = gp_song.tracks[0].measures[0]
    gp_time_signature = gp_measure.timeSignature
    is_repeat_open = gp_measure.header.isRepeatOpen
    repeat_close = gp_measure.header.repeatClose
    assert type(gp_measure) == gm.models.Measure
    assert type(gp_time_signature) == gm.models.TimeSignature
    m21_measure = gp_to_m21_convertor._create_m21_measure(
        0, 0, gp_time_signature, is_repeat_open, repeat_close
    )
    assert type(m21_measure) == m21.stream.Measure
    assert m21_measure.timeSignature.ratioString == "4/4"
    m21_tempo = m21_measure.recurse().getElementsByClass(m21.tempo.MetronomeMark)[0]
    assert m21_tempo.number == 70


def test_create_new_m21_voice(gp_to_m21_convertor):
    gp_song = gp_to_m21_convertor.gp_stream
    gp_voice = gp_song.tracks[0].measures[0].voices[0]
    assert type(gp_voice) == gm.models.Voice
    m21_voice = gp_to_m21_convertor._create_m21_voice(0)
    assert type(m21_voice) == m21.stream.Voice
    assert m21_voice.id == "voice_0"


def test_create_m21_note(gp_to_m21_convertor):
    gp_song = gp_to_m21_convertor.gp_stream
    m21_voice = gp_song.tracks[0].measures[0].voices[0]
    gp_beat = gp_song.tracks[0].measures[0].voices[0].beats[0]
    gp_note = gp_beat.notes[0]
    assert type(gp_note) == gm.models.Note
    m21_note = gp_to_m21_convertor._create_m21_note(0, gp_beat, gp_note, m21_voice)
    assert type(m21_note) == m21.note.Note
    assert m21_note.nameWithOctave == "E4"
    assert m21_note.quarterLength == 0.5
    assert m21_note.duration.dots == 0


def test_apply(gp_to_m21_convertor):
    m21_stream = gp_to_m21_convertor.apply()
    m21_stream.write("midi", "test_1.mid")


def test_apply_metallica():
    test_folder_path = Path.home() / "GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    gp_file = gp_serializer.load(
        test_folder_path / "Metallica - Nothing else matters (7).gp3.gp2tokens2gp.gp5"
    )
    gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
    m21_stream = gp_to_m21_convertor.apply()
    m21_stream.write("midi", "test_met_3.mid")


def test_calculate_measure_duration_in_ticks():
    test_folder_path = Path.home() / "GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    gp_file = gp_serializer.load(
        test_folder_path / "Metallica - Nothing else matters (7).gp3.gp2tokens2gp.gp5"
    )
    gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
    ts_1 = m21.meter.TimeSignature("4/4")
    m1_duration = gp_to_m21_convertor._calculate_measure_duration_in_ticks(ts_1)
    assert m1_duration == 4 * 960
    ts_2 = m21.meter.TimeSignature("6/8")
    m2_duration = gp_to_m21_convertor._calculate_measure_duration_in_ticks(ts_2)
    assert m2_duration == 6 * 480
    ts_3 = m21.meter.TimeSignature("3/4")
    m3_duration = gp_to_m21_convertor._calculate_measure_duration_in_ticks(ts_3)
    assert m3_duration == 3 * 960
    ts_4 = m21.meter.TimeSignature("1/4")
    m4_duration = gp_to_m21_convertor._calculate_measure_duration_in_ticks(ts_4)
    assert m4_duration == 960
    ts_5 = m21.meter.TimeSignature("7/32")
    m5_duration = gp_to_m21_convertor._calculate_measure_duration_in_ticks(ts_5)
    assert m5_duration == 7 * 120
