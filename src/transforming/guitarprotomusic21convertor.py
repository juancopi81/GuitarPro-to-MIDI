from guitarpro.models import Song
from music21.stream.base import Score
from music21 import stream, metadata


class GuitarProToMusic21Convertor:
    """Converts a PyGuitarPro strem into a Music21 Stream"""

    def __init__(self,
                 gp_stream: Song) -> None:
        self.gp_stream = gp_stream
        self.metadata = self._get_metadata()

    def _get_metadata(self) -> dict:
        title = str(self.gp_stream.title)
        artist = str(self.gp_stream.artist)
        tempo = self.gp_stream.tempo
        return {
            "title": title,
            "artist": artist,
            "tempo": tempo
        }

    def apply(self) -> Score:
        m21_score = self._create_new_m21_score()
        return m21_score

    def _create_new_m21_score(self):
        new_empty_score = stream.Score()
        new_empty_score.insert(0, metadata.Metadata())
        new_empty_score.metadata.title =(self.metadata["title"]).split(".")[0]
        new_empty_score.metadata.composer = self.metadata["artist"]
        return new_empty_score 