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
                # Create measure
                m21_measure = self._create_m21_measure(idx_track, idx_measure, gp_measure)
                # Loop over voices
                for idx_voice, gp_voice in enumerate(gp_measure.voices):
                    # If voice is empty, continue
                    if gp_voice.isEmpty:
                        continue
                    # Create voice
                    m21_voice = self._create_m21_voice(idx_voice, gp_voice)
                    # Append voice to measure
                    m21_measure.insert(0, m21_voice)
                    # Loop over beats and notes
                    for idx_beat, gp_beat in enumerate(gp_voice.beats):
                        # Update the previous_beat_duration for the next beat
                        offset = gp_beat.startInMeasure / QUARTER_TIME_IN_TICKS
                        for gp_note in gp_beat.notes:
                            m21_note = self._create_m21_note(idx_beat, gp_beat, gp_note, m21_measure)
                            m21_note.offset = offset
                            m21_voice.insert(offset, m21_note)
                m21_part.append(m21_measure)
            self.m21_score.append(m21_part)
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
        m21_time_signature.priority = -1

        if idx_measure == 0:
            m21_measure.append(self.metronome)
            m21_measure.timeSignature = m21_time_signature 
            self.time_signature = m21_time_signature
        # If time signature is different from last time signature, insert ts to measure
        elif self.time_signature.numerator != m21_numerator or self.time_signature.denominator != m21_denominator:
            m21_measure.timeSignature = m21_time_signature 
            self.time_signature = m21_time_signature

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
                         gp_note: gm.models.Note,
                         m21_measure: m21.stream.Measure) -> m21.note.Note:
        # Retrieve the duration of the beat
        gp_duration = gp_beat.duration.value
        m21_duration_name = m21.duration.typeFromNumDict[float(gp_duration)]

        # Check tempo changes
        if gp_beat.effect.mixTableChange != None:
            if gp_beat.effect.mixTableChange.tempo.value != None:
                new_metronome = m21.tempo.MetronomeMark(number=gp_beat.effect.mixTableChange.tempo.value)
                for el in m21_measure.recurse():
                    if "MetronomeMark" in el.classes:
                        el.activeSite.remove(el)
                    
                m21_measure.insert(0, new_metronome)

        # Add dot if necessary
        if gp_beat.duration.isDotted:
            m21_dots = 1
        else:
            m21_dots = 0

        # Check if type of note = normal note
        if gp_note.type.value == 1:
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(pitch=midi_value,
                                     type=m21_duration_name,
                                     dots=m21_dots)

        # Check if tie note
        elif gp_note.type.value == 2:
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(pitch=midi_value,
                                     type=m21_duration_name,
                                     dots=m21_dots)
            # print(f"{gp_note.realValue} {gp_note.value} {gp_note.string}")
            # # midi_value = gp_note.realValue
            # # m21_note = m21.note.Note(midi_value)
            # # m21_note.duration = m21_duration
            # # m21_note.tie = m21.tie.Tie("stop")
            # midi_value = gp_note.realValue
            # m21_note = m21.note.Note(midi_value)
            # m21_note.duration = m21_duration
            # # Since we don't have tie direction information in the PyGuitarPro library,
            # # we'll use a simple workaround by checking if a note with the same pitch
            # # already exists in the current voice. If it does, we'll set the previous
            # # note's tie type to 'start' and the current note's tie type to 'stop'
            # for element in reversed(m21_voice.elements):
            #     if isinstance(element, m21.note.Note) and element.pitch == m21_note.pitch:
            #         element.tie = m21.tie.Tie('start')
            #         m21_note.tie = m21.tie.Tie('stop')
            #         break
            # else:
            #     m21_note.tie = m21.tie.Tie('stop')
        # If not, is a rest, to handle dead notes
        else:
            print(f"Else {gp_note}")
            m21_note = m21.note.Rest(type=m21_duration_name)

        return m21_note