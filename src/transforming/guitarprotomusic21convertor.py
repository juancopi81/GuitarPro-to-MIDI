from typing import Union

import guitarpro as gm
import music21 as m21


QUARTER_TIME_IN_TICKS = 960


class GuitarProToMusic21Convertor:
    """Converts a PyGuitarPro stream into a Music21 Stream"""

    def __init__(self, gp_stream: gm.models.Song) -> None:
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
        return {"title": title, "artist": artist, "tempo": tempo}

    @property
    def time_signature(self) -> m21.meter.TimeSignature:
        return self._time_signature

    @time_signature.setter
    def time_signature(self, m21_time_signature: m21.meter.TimeSignature) -> None:
        self._time_signature = m21_time_signature

    def apply(self) -> m21.stream.Score:
        tracks = self.gp_stream.tracks
        # Loop over each track of the song object
        for idx_track, track in enumerate(tracks):
            # Create part and append it to score
            m21_part = self._create_m21_part(idx_track, track)
            self.m21_score.append(m21_part)
            # Loop over measure
            for idx_measure, gp_measure in enumerate(track.measures):
                # Create measure and append it to part
                m21_measure = self._create_m21_measure(
                    idx_track, idx_measure, gp_measure
                )
                m21_part.append(m21_measure)
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
                            if gp_beat.duration.isDotted:
                                m21_dots = 1
                            else:
                                m21_dots = 0
                            m21_duration_name = m21.duration.typeFromNumDict[
                                float(gp_beat.duration.value)
                            ]
                            m21_rest = m21.note.Rest(
                                type=m21_duration_name, dots=m21_dots
                            )
                            m21_rest.offset = offset
                            m21_voice.insert(offset, m21_rest)
                        else:
                            for gp_note in gp_beat.notes:
                                m21_note = self._create_m21_note(
                                    idx_beat,
                                    gp_beat,
                                    gp_note,
                                    m21_measure,
                                )
                                m21_note.offset = offset
                                # Update last active note on string
                                if gp_note.type.value == 1:
                                    self._last_normal_notes = (
                                        self._update_string_last_normal_note(
                                            gp_note, m21_note, idx_measure
                                        )
                                    )
                                # If note is of type tie, find the last active note on _last_normal_notes dict.
                                elif gp_note.type.value == 2:
                                    string_number = gp_note.string
                                    if string_number in self._last_normal_notes:
                                        last_normal_note = self._last_normal_notes[
                                            string_number
                                        ]["m21_note"]
                                        last_normal_measure = self._last_normal_notes[
                                            string_number
                                        ]["measure"]
                                        m21_note.pitch = last_normal_note.pitch
                                        if idx_measure == last_normal_measure:
                                            offset_difference = (
                                                m21_note.offset
                                                - last_normal_note.offset
                                            )
                                            # Calculate remaining
                                            remaining_duration = (
                                                offset_difference
                                                - last_normal_note.duration.quarterLength
                                            )
                                        else:
                                            # TODO Substract last_normal_note duration from measure duration
                                            remaining_duration = 0
                                        last_normal_note.tie = m21.tie.Tie("start")
                                        last_normal_note.duration.quarterLength += (
                                            remaining_duration
                                            + m21_note.duration.quarterLength
                                        )
                                        continue
                                # Insert note into current voice
                                m21_voice.insert(offset, m21_note)
                        if (len(gp_voice.beats) - 1) == idx_beat:
                            remaining_rests = self._calculate_remaining_rests(gp_beat)
                            if remaining_rests != None:
                                m21_voice.append(remaining_rests)
        return self.m21_score

    def _create_new_m21_score(self):
        new_empty_score = m21.stream.Score()
        new_empty_score.insert(0, m21.metadata.Metadata())
        new_empty_score.metadata.title = (self.metadata["title"]).split(".")[0]
        new_empty_score.metadata.composer = self.metadata["artist"]
        return new_empty_score

    def _create_m21_part(
        self, idx_track: int, track: gm.models.Track
    ) -> m21.stream.Part:
        # Get instrument's MIDI id
        instrument_id = track.channel.instrument
        track_name = track.name
        # Create part and add instrument
        m21_part = m21.stream.Part(id=f"name_{track_name}_{idx_track}")
        if track.isPercussionTrack:
            part_inst = m21.instrument.UnpitchedPercussion()
            part_inst.midiChannel = 9
            part_inst.inGMPercMap = False
        else:
            part_inst = m21.instrument.instrumentFromMidiProgram(instrument_id)
        part_inst.priority = -2
        m21_part.insert(0, part_inst)
        return m21_part

    def _create_m21_measure(
        self, idx_part: int, idx_measure: int, gp_measure: gm.models.Measure
    ) -> m21.stream.Measure:
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
        m21_time_signature = m21.meter.TimeSignature(
            f"{m21_numerator}/{m21_denominator}"
        )
        m21_time_signature.priority = -1

        if idx_measure == 0:
            m21_measure.append(self.metronome)
            m21_measure.timeSignature = m21_time_signature
            self.time_signature = m21_time_signature
        # If time signature is different from last time signature, insert ts to measure
        elif (
            self.time_signature.numerator != m21_numerator
            or self.time_signature.denominator != m21_denominator
        ):
            m21_measure.timeSignature = m21_time_signature
            self.time_signature = m21_time_signature

        # Add repetition if necessary
        if gp_measure.header.isRepeatOpen:
            m21_measure.leftBarline = m21.bar.Repeat(direction="start")
        if gp_measure.header.repeatClose > 0:
            m21_measure.rightBarline = m21.bar.Repeat(
                direction="end", times=gp_measure.header.repeatClose
            )

        return m21_measure

    def _create_m21_voice(
        self, idx_voice: int, gp_voice: gm.models.Voice
    ) -> m21.stream.Voice:
        m21_voice = m21.stream.Voice(id=f"voice_{idx_voice}")
        return m21_voice

    def _create_m21_note(
        self,
        idx_beat: int,
        gp_beat: gm.models.Beat,
        gp_note: gm.models.Note,
        m21_measure: m21.stream.Measure,
    ) -> m21.note.Note:
        # Retrieve the duration of the beat
        gp_duration = gp_beat.duration.value
        m21_duration_name = m21.duration.typeFromNumDict[float(gp_duration)]

        # Check tempo changes
        if gp_beat.effect.mixTableChange != None:
            if gp_beat.effect.mixTableChange.tempo != None:
                if gp_beat.effect.mixTableChange.tempo.value != None:
                    new_metronome = m21.tempo.MetronomeMark(
                        number=gp_beat.effect.mixTableChange.tempo.value
                    )
                    for el in m21_measure.recurse():
                        if "MetronomeMark" in el.classes:
                            el.activeSite.remove(el)
                    m21_measure.insert(0, new_metronome)

        # Add dot if necessary
        if gp_beat.duration.isDotted:
            m21_dots = 1
        else:
            m21_dots = 0

        # Check if type of note is normal or tie note
        if (
            gp_note.type.value == 1
            or gp_note.type.value == 2
            or gp_note.type.value == 3
        ):
            # TODO: Solve death notes
            midi_value = gp_note.realValue
            m21_note = m21.note.Note(
                pitch=midi_value, type=m21_duration_name, dots=m21_dots
            )
        else:
            print(f"Else {gp_note}")
            m21_note = m21.note.Rest(type=m21_duration_name)

        # Add tuplets if neccesary
        if gp_beat.duration.tuplet != gm.models.Tuplet(enters=1, times=1):
            tuplet_enters = gp_beat.duration.tuplet.enters
            tuplet_times = gp_beat.duration.tuplet.times
            m21_note.duration.appendTuplet(
                m21.duration.Tuplet(tuplet_enters, tuplet_times)
            )

        return m21_note

    def _update_string_last_normal_note(
        self, gp_note: gm.models.Note, m21_note: m21.note.Note, measure_number: int
    ) -> dict:
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
            "string_value": string_number,
            "measure": measure_number,
        }

        # Return the dictionary
        return self._last_normal_notes

    @staticmethod
    def _calculate_measure_duration_in_ticks(
        time_signature: m21.meter.TimeSignature,
    ) -> int:
        """Returns the duration in ticks of a mesure, given its time signature.
        QUARTER_TIME_IN_TICKS = 960
        """
        current_numerator = time_signature.numerator
        current_denominator = time_signature.denominator
        beat_duration = QUARTER_TIME_IN_TICKS * (4 / current_denominator)
        return int(beat_duration * current_numerator)

    def _calculate_remaining_rests(
        self, gp_beat: gm.models.Beat
    ) -> Union[m21.note.Rest, None]:
        total_duration_of_beats = gp_beat.startInMeasure + gp_beat.duration.time
        measure_total_duration = self._calculate_measure_duration_in_ticks(
            self.time_signature
        )
        remaining_beats = measure_total_duration - total_duration_of_beats
        # If measure is complete, return None
        if remaining_beats == 0:
            return None

        # Create a rest that completes the remaining of the measure
        remaining_duration_quarter_length = remaining_beats / QUARTER_TIME_IN_TICKS
        remaining_rest = m21.note.Rest(remaining_duration_quarter_length)
        return remaining_rest


gp_file = gm.parse(
    "/home/juancopi81/GuitarPro-to-MIDI/src/test/test_files/progmetal.gp3"
)
gp_to_m21_convertor = GuitarProToMusic21Convertor(gp_file)
m21_stream = gp_to_m21_convertor.apply()
m21_stream.write("mid", "prog_t_rests.mid", quantizePost=False)
