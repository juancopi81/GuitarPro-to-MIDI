from guitarpro.models import Song, Track
from music21.stream.base import Score
from music21 import stream, metadata, instrument


class GuitarProToMusic21Convertor:
    """Converts a PyGuitarPro stream into a Music21 Stream"""

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
        tracks = self.gp_stream.tracks
        # Loop over each track of the song object
        for idx_track, track in enumerate(tracks):
            m21_part = self._create_m21_part(idx_track, track)
            # TODO Loop over measure, voices, beats, and notes
            for gp_measure in m21_part.measures():
                m21_measure = stream.Measure()
        return m21_score

    def _create_new_m21_score(self):
        new_empty_score = stream.Score()
        new_empty_score.insert(0, metadata.Metadata())
        new_empty_score.metadata.title =(self.metadata["title"]).split(".")[0]
        new_empty_score.metadata.composer = self.metadata["artist"]
        return new_empty_score

    def _create_m21_part(self,
                         idx_track: int,
                         track: Track) -> stream.Part:
        # Get instrument's MIDI id
        instrument_id = track.channel.instrument
        track_name = track.name
        # Create part and add instrument
        m21_part = stream.Part(id=f"name_{track_name}_{idx_track}")
        part_inst = instrument.instrumentFromMidiProgram(instrument_id)
        m21_part.append(part_inst)
        return m21_part