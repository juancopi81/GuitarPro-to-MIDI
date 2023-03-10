import os
from pathlib import Path

import guitarpro as gm
from guitarpro.models import Song
from music21.stream.base import Score
from music21 import *

from src.loading.serialization import PyGuitarProSerializer
from src.loading.serialization import Music21Serializer


def test_guitarpro_serializer_load():
    test_folder_path = Path.home()/"GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    stream = gp_serializer.load(test_folder_path/"Antonio Carlos, Jobim - Engano.gp4.gp2tokens2gp.gp5")
    assert type(stream) == Song


def test_guitarpro_serializer_dump():    
    test_folder_path = Path.home()/"GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    
    splits = [([(0, 6), (2, 5)], 4),
          ([(3, 6), (5, 5)], 4),
          ([(5, 6), (7, 5)], 4),
          ([(0, 6), (2, 5)], 4)]

    base_song = gm.Song()
    track = gm.Track(base_song, measures=[])
    base_song.tracks.append(track)

    m = 0  # number of measure to be edited
    header = base_song.measureHeaders[m]
    measure = gm.Measure(track, header)
    track.measures.append(measure)

    voice = measure.voices[0]

    for i, (notes, duration) in enumerate(splits):
        new_duration = gm.Duration(value=duration)
        new_beat = gm.Beat(voice,
                           duration=new_duration,
                           status=gm.BeatStatus.normal)
        for value, string in notes:
            new_note = gm.Note(new_beat,
                               value=value,
                               string=string,
                               type=gm.NoteType.normal)
            new_beat.notes.append(new_note)
        voice.beats.append(new_beat)

    save_path = test_folder_path/"test_gp_file.gp5"
    gp_serializer.dump(base_song, save_path)
    assert save_path.is_file() == True
    os.remove(save_path)


def test_music21_serializer_load():
    test_folder_path = Path.home()/"GuitarPro-to-MIDI/src/test/test_files"
    m21_serializer = Music21Serializer()
    m21_stream = m21_serializer.load(test_folder_path/"SixStudiesC.mid")
    assert type(m21_stream) == Score



def test_music21_serializer_dump():
    test_folder_path = Path.home()/"GuitarPro-to-MIDI/src/test/test_files"
    m21_serializer = Music21Serializer()
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure()
    m.append(note.Note())
    p.append(m)
    s.append(p)
    s.insert(0, metadata.Metadata())
    s.metadata.title = 'title'
    s.metadata.composer = 'composer'
    save_path = test_folder_path/"test_midi_file.mid"
    m21_serializer.dump(m21_stream=s, save_path=save_path)
    assert save_path.is_file() == True
    os.remove(save_path)