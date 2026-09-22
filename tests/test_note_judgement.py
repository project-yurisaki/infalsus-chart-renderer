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

from if_chart.elements import Chart, DirectionalFlick, Hold, SkyArea, Tap
from if_chart.note_judgement import (
    get_chart_judgement_points,
    get_combo_before,
    get_judgement_points,
)


class NoteJudgementTests(unittest.TestCase):
    def test_hold_has_leading_point_while_skyarea_does_not(self):
        hold = get_judgement_points(0, 600, 120, True)
        skyarea = get_judgement_points(0, 600, 120, False)

        self.assertEqual(hold, [0, 250, 500, 600])
        self.assertEqual(skyarea, [250, 500, 600])

    def test_chart_points_include_short_and_long_objects(self):
        chart = Chart(
            [
                Tap(0, lane=2, width=1),
                DirectionalFlick(100, 0.5, 0.25, 4),
                Hold(200, lane=2, width=1, duration=600),
                SkyArea(300, 0.5, 0.25, 0.5, 0.25, 0, 0, 600, 1),
            ],
            120,
            4,
        )

        self.assertEqual(
            get_chart_judgement_points(chart),
            [0, 100, 200, 450, 550, 700, 800, 800, 900],
        )

    def test_combo_before_excludes_points_on_the_bar_line(self):
        points = [0, 100, 200, 450, 550, 700, 800, 800, 900]

        self.assertEqual(get_combo_before(points, 800), 6)
        self.assertEqual(get_combo_before(points, 801), 8)


if __name__ == "__main__":
    unittest.main()
