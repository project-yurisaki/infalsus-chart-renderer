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

import unittest

from if_chart.elements import (
    BpmChange,
    Chart,
    DirectionalFlick,
    Hold,
    SkyArea,
    Tap,
)
from if_chart.notes import BeatNote, analyze_notes


class BeatNoteTests(unittest.TestCase):
    def test_common_and_dotted_note_values(self):
        quarter = BeatNote()
        dotted_eighth = BeatNote()

        self.assertTrue(quarter.analyze_note(0, 500, 120))
        self.assertEqual(quarter.display, "4")
        self.assertTrue(dotted_eighth.analyze_note(0, 375, 120))
        self.assertEqual(dotted_eighth.display, "8.")

    def test_duration_beyond_full_note(self):
        note = BeatNote()

        self.assertTrue(note.analyze_note(0, 2100, 120))
        self.assertEqual(note.display, "-")


class AnalyzeNotesTests(unittest.TestCase):
    def test_uses_hold_start_and_each_skyarea_statement(self):
        events = [
            Tap(0, lane=2, width=1),
            Hold(500, lane=2, width=1, duration=1000),
            SkyArea(750, 0.5, 0.25, 0.5, 0.25, 0, 0, 1000, 1),
            DirectionalFlick(1000, 0.5, 0.25, 4),
        ]

        notes = analyze_notes(Chart(events, 120, 4))

        self.assertEqual([note.time_point for note in notes], [0, 500, 750])
        self.assertEqual([note.display for note in notes], ["4", "8", "8"])

    def test_uses_bpm_at_current_object(self):
        events = [
            Tap(0, lane=2, width=1),
            BpmChange(1000, 240, 4),
            Tap(1000, lane=2, width=1),
            Tap(1250, lane=2, width=1),
        ]

        notes = analyze_notes(Chart(events, 120, 4))

        self.assertEqual(notes[-1].display, "4")


if __name__ == "__main__":
    unittest.main()
