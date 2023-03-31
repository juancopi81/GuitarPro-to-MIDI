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
        # Dictionary to keep track of last note on each string
        self._last_normal_notes = {}
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
                        if len(gp_beat.notes) == 0:
                            m21_duration_name = m21.duration.typeFromNumDict[float(gp_beat.duration.value)]
                            m21_rest = m21.note.Rest(type=m21_duration_name)
                            m21_voice.insert(offset, m21_rest)
                        else:
                            for gp_note in gp_beat.notes:
                                m21_note = self._create_m21_note(idx_beat, gp_beat, gp_note, m21_measure)
                                m21_note.offset = offset
                                # Update last active note on string
                                if gp_note.type.value == 1:
                                    self._last_normal_notes = self._update_string_last_normal_note(gp_note, m21_note)
                                # If note is of type tie, find the last active note on _last_normal_notes dict.
                                elif gp_note.type.value == 2:
                                    string_number = gp_note.string
                                    if string_number in self._last_normal_notes:
                                        last_normal_note = self._last_normal_notes[string_number]["m21_note"]
                                        m21_note.pitch = last_normal_note.pitch
                                        offset_difference = m21_note.offset - last_normal_note.offset
                                        remaining_duration = offset_difference - last_normal_note.duration.quarterLength
                                        last_normal_note.tie = m21.tie.Tie("start")
                                        last_normal_note.duration.quarterLength += remaining_duration + m21_note.duration.quarterLength
                                        continue
                                # Insert note into current voice
                                m21_voice.insert(offset, m21_note)
                m21_part.append(m21_measure)
            self.m21_score.append(m21_part)
            self.m21_score.show("text")
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
        if gp_note.type.value == 1 or gp_note.type.value == 2:
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(pitch=midi_value,
                                     type=m21_duration_name,
                                     dots=m21_dots)
        else:
            print(f"Else {gp_note}")
            m21_note = m21.note.Rest(type=m21_duration_name)

        return m21_note
    
    def _update_string_last_normal_note(self,
                                        gp_note: gm.models.Note,
                                        m21_note: m21.note.Note) -> dict:
        """Update and returns a dictionary containing the following information for each string:
            - The associated m21_note
            - The realValue of that string
            - Tha value of the string
        """ 
        # Get the string number
        string_number = gp_note.string
        # Get the real value
        midi_value = gp_note.realValue
        # Create the dictionary if it does not exist yet
        if self._last_normal_notes is None:
            self._last_normal_notes = {}

        # Update the dictionary
        self._last_normal_notes[string_number] = {
            "m21_note": m21_note,
            "midi_value": midi_value,
            "string_value": string_number
        }

        # Return the dictionary
        return self._last_normal_notes

gp_file = gm.parse("/home/juancopi81/GuitarPro-to-MIDI/src/test/test_files/Antonio Carlos, Jobim - Engano.gp4.gp2tokens2gp.gp5")
gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
m21_stream = gp_to_m21_convertor.apply()
m21_stream.write("mid", "test_an_12.mid")