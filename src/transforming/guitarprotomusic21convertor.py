import guitarpro as gm
import music21 as m21


QUARTER_TIME_IN_TICKS = 960


class GuitarProToMusic21Convertor:
    """Converts a PyGuitarPro stream into a Music21 Stream"""

    def __init__(self,
                 gp_stream: gm.models.Song) -> None:
        self.gp_stream = gp_stream
        self.metadata = self._get_metadata()
        self.m21_score = self._create_new_m21_score()
        # Create a global metronome for the song
        self.metronome = m21.tempo.MetronomeMark(number=self.metadata["tempo"])
        self._time_signature = m21.meter.TimeSignature()

    def _get_metadata(self) -> dict:
        title = str(self.gp_stream.title)
        artist = str(self.gp_stream.artist)
        tempo = self.gp_stream.tempo
        return {
            "title": title,
            "artist": artist,
            "tempo": tempo
        }

    @property
    def time_signature(self) -> m21.meter.TimeSignature:
        return self._time_signature

    @time_signature.setter
    def time_signature(self, m21_time_signature = m21.meter.TimeSignature) -> None:
        self._time_signature = m21_time_signature

    def apply(self) -> m21.stream.Score:
        tracks = self.gp_stream.tracks
        # Loop over each track of the song object
        for idx_track, track in enumerate(tracks):
            m21_part = self._create_m21_part(idx_track, track)
            # Loop over measure
            for idx_measure, gp_measure in enumerate(track.measures):
                m21_measure = self._create_m21_measure(idx_track, idx_measure, gp_measure)
                # Loop over voices
                for idx_voice, gp_voice in enumerate(gp_measure.voices):
                    m21_voice = self._create_m21_voice(idx_voice, gp_voice)
                    # Loop over beats and notes
                    for idx_beat, gp_beat in enumerate(gp_voice.beats):
                        for gp_note in gp_beat.notes:
                            m21_note = self._create_m21_note(idx_beat, gp_beat, gp_note)
                            insert_quarter_note = gp_beat.startInMeasure / QUARTER_TIME_IN_TICKS
                            m21_voice.insert(insert_quarter_note, m21_note)
                    m21_measure.insert(idx_voice, m21_voice)
                m21_part.insert(idx_measure, m21_measure)
            self.m21_score.insert(idx_track, m21_part)
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
        if gp_time_signature.denominator.isDotted:
            m21_denominator *= 1.5
        if m21_numerator == 0:
            m21_numerator = 1
        elif m21_denominator == 0:
            m21_numerator = 1
        m21_time_signature = m21.meter.TimeSignature(f"{m21_numerator}/{m21_denominator}")
        self.time_signature = m21_time_signature

        # If first measure of part, add time signature and tempo
        if idx_measure == 0:
            m21_measure.append(self.metronome)
            m21_measure.insert(0, self.time_signature)
        # If time signature is different from last time signature, insert ts to measure
        elif self.time_signature.numerator != m21_numerator or self.time_signature.denominator != m21_denominator:
            m21_measure.insert(0, self.time_signature)

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
        m21_duration = m21.duration.Duration()
        m21_duration.quarterLength = 4 / event_duration
        # Add dot if necessary
        if gp_beat.duration.isDotted:
            m21_duration.dots = 1

        # Check if type of note = normal note
        if gp_note.type.value == 1:
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(midi_value)
            m21_note.duration = m21_duration
        # If not, is a rest, to handle tie and dead notes
        else:
            m21_note = m21.note.Rest()
            m21_note.duration = m21_duration

        return m21_note