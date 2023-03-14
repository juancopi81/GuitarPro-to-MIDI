import guitarpro as gm
import music21 as m21


class GuitarProToMusic21Convertor:
    """Converts a PyGuitarPro stream into a Music21 Stream"""

    def __init__(self,
                 gp_stream: gm.models.Song) -> None:
        self.gp_stream = gp_stream
        self.metadata = self._get_metadata()
        self.m21_score = self._create_new_m21_score()
        # Create a global metronome for the song
        self.metronome = m21.tempo.MetronomeMark(number=self.metadata["tempo"])

    def _get_metadata(self) -> dict:
        title = str(self.gp_stream.title)
        artist = str(self.gp_stream.artist)
        tempo = self.gp_stream.tempo
        return {
            "title": title,
            "artist": artist,
            "tempo": tempo
        }

    def apply(self) -> m21.stream.Score:
        tracks = self.gp_stream.tracks
        # Loop over each track of the song object
        for idx_track, track in enumerate(tracks):
            m21_part = self._create_m21_part(idx_track, track)
            # Loop over measure
            for idx_measure, gp_measure in enumerate(track.measures()):
                m21_measure = self._create_m21_measure(idx_track, idx_measure, gp_measure)
                # Loop over voices
                for idx_voice, gp_voice in enumerate(gp_measure):
                    m21_voice = self._create_m21_voice(idx_voice, gp_voice)
                    # Loop over beats and notes
                    for idx_beat, gp_beat in enumerate(gp_voice.beats):
                        for gp_note in gp_beat.notes:
                            m21_note = self._create_m21_note(idx_beat, gp_beat, gp_note)
        return self.m21_score

    def _create_new_m21_score(self):
        new_empty_score = m21.stream.Score()
        new_empty_score.insert(0, m21.metadata.Metadata())
        new_empty_score.metadata.title =(self.metadata["title"]).split(".")[0]
        new_empty_score.metadata.composer = self.metadata["artist"]
        return new_empty_score

    def _create_m21_part(self,
                         idx_track: int,
                         track: gm.models.Track) -> m21.stream.Part:
        # Get instrument's MIDI id
        instrument_id = track.channel.instrument
        track_name = track.name
        # Create part and add instrument
        m21_part = m21.stream.Part(id=f"name_{track_name}_{idx_track}")
        part_inst = m21.instrument.instrumentFromMidiProgram(instrument_id)
        m21_part.append(part_inst)
        return m21_part

    def _create_m21_measure(self,
                            idx_part: int,
                            idx_measure: int,
                            gp_measure: gm.models.Measure) -> m21.stream.Measure:
        # Create a new m21_measure
        m21_measure = m21.stream.Measure(id=f"part_{idx_part}_measure_{idx_measure}")

        # Get time signature of measure
        gp_time_signature = gp_measure.timeSignature
        m21_numerator = gp_time_signature.numerator
        m21_denominator = gp_time_signature.denominator.value
        m21_time_signature = m21.meter.TimeSignature(f"{m21_numerator}/{m21_denominator}")

        # If first measure of part, add time signature and tempo
        if idx_measure == 0:
            m21_measure.append(self.metronome)
            m21_measure.insert(0, m21_time_signature)
        # If time signature is different from last time signature, insert ts to measure
        elif self.m21_score.recurse().getElementsByClass(m21.meter.TimeSignature)[-1] != m21_time_signature:
            m21_measure.insert(0, m21_time_signature)

        # Add repetition if necessary
        if gp_measure.header.isRepeatOpen:
            m21_measure.leftBarline = m21.bar.Repeat(direction="start")
        if gp_measure.header.repeatClose > 0:
            m21_measure.rightBarline = m21.bar.Repeat(direction="end", times=gp_measure.header.repeatClose)

        return m21_measure

    def _create_m21_voice(self,
                          idx_voice: int,
                          gp_voice: gm.models.Voice) -> m21.stream.Voice:
        m21_voice = m21.stream.Voice(id=f"voice_{idx_voice}")
        return m21_voice

    def _create_m21_note(self,
                         idx_beat: int,
                         gp_beat: gm.models.Beat,
                         gp_note: gm.models.Note) -> m21.stream.Voice:
        # Retrieve the duration of the beat
        event_duration = gp_beat.duration.value
        # Add dot if necessary
        if gp_beat.duration.isDotted:
            event_duration.dots = 1

        # Check if type of note = normal note
        if gp_note.type.value == 1:
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(midi_value)
            m21_note.quarterLength = event_duration
        # If not, is a rest, to handle tie and dead notes
        else:
            m21_note = m21.note.Rest()
            m21_note.quarterLength = event_duration

        return m21_note