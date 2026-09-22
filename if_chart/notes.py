#     Copyright 2026 Rosemoe
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from fractions import Fraction

from .elements import (
    BpmChange,
    Chart,
    DirectionalFlick,
    Hold,
    SkyArea,
    Tap,
)


class BeatNote:
    def __init__(self) -> None:
        self.time_point = 0
        self.duration = 0
        self.display = ''
        self.note_value: Fraction | None = None

    def analyze_note(self, timing: int, length: int, bpm: float) -> bool:
        self.time_point = timing
        self.duration = length
        if bpm == 0:
            return False

        threshold = 3.5
        time_full_note = 60 * 1000 * 4 / bpm
        if length > time_full_note + threshold:
            self.display = '-'
            return True

        denominators = [56, 64, 72, 80, 96]
        best_note_value = None
        best_error = float('inf')
        for denominator in denominators:
            unit_duration = time_full_note / denominator
            quotient = round(length / unit_duration)
            error = abs(length - quotient * unit_duration)
            note_value = Fraction(quotient, denominator)
            if error < best_error:
                best_error = error
                best_note_value = note_value

        if best_note_value and best_error <= threshold:
            if best_note_value.numerator > 9:
                return False
            self.note_value = best_note_value
            division = 1 / best_note_value
            if division.denominator == 1:
                self.display = str(division.numerator)
            elif (
                division.denominator == 3
                and division.numerator > 2
                and division.numerator % 2 == 0
            ):
                dotted_value = division * Fraction(3, 2)
                self.display = f"{dotted_value.numerator}."
            else:
                self.display = f"{division.numerator}/{division.denominator}"
            return True
        return False


def _get_bpm_at(chart: Chart, timestamp: int) -> float:
    bpm = chart.bpm
    for change in sorted(
        (event for event in chart.events if isinstance(event, BpmChange)),
        key=lambda event: event.timestamp,
    ):
        if change.timestamp > timestamp:
            break
        bpm = change.bpm
    return bpm


def analyze_notes(chart: Chart) -> list[BeatNote]:
    note_types = (Tap, Hold, SkyArea, DirectionalFlick)
    time_points = sorted(
        event.timestamp
        for event in chart.events
        if isinstance(event, note_types)
    )
    result = []
    for index in range(len(time_points) - 1):
        delta_time = time_points[index + 1] - time_points[index]
        if delta_time <= 3:
            continue

        time_point = time_points[index]
        note = BeatNote()
        if not note.analyze_note(
            time_point,
            delta_time,
            _get_bpm_at(chart, time_point),
        ):
            note.analyze_note(time_point, delta_time, chart.bpm)
        result.append(note)
    return result
