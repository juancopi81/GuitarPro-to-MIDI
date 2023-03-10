from pathlib import Path

from pytest import fixture
from guitarpro.models import Song
from music21.stream.base import Score

from src.loading.serialization import PyGuitarProSerializer
from src.transforming.guitarprotomusic21convertor import GuitarProToMusic21Convertor


@fixture
def gp_to_m21_convertor():
    test_folder_path = Path.home()/"GuitarPro-to-MIDI/src/test/test_files"
    gp_serializer = PyGuitarProSerializer()
    gp_file = gp_serializer.load(test_folder_path/"Antonio Carlos, Jobim - Engano.gp4.gp2tokens2gp.gp5")
    gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
    return gp_to_m21_convertor


def test_guitarpro_to_music21_convertor_init(gp_to_m21_convertor):    
    metadata = gp_to_m21_convertor.metadata
    assert type(gp_to_m21_convertor.gp_stream) == Song
    assert type(metadata) == dict
    assert metadata["title"] == "Antonio Carlos, Jobim - Engano.gp4"
    assert metadata["artist"] == "Antonio Carlos, Jobim"
    assert metadata["tempo"] == 70


def test_create_new_m21_score(gp_to_m21_convertor):
    new_m21_score = gp_to_m21_convertor._create_new_m21_score()
    assert type(new_m21_score) == Score
    assert new_m21_score.metadata.title == "Antonio Carlos, Jobim - Engano"
    assert new_m21_score.metadata.composer == "Antonio Carlos, Jobim"