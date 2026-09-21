import unittest

from if_chart.elements import BpmChange, Chart, Tap, TrackSpeedChange
from if_chart.renderer import (
    RenderContext,
    _beat_line_timestamps_with_bounds,
    _format_bpm,
    _format_chart_time,
    _page_boundaries,
)


class PageLayoutTests(unittest.TestCase):
    def test_chart_time_format(self):
        self.assertEqual(_format_chart_time(0), "0:00.0")
        self.assertEqual(_format_chart_time(61540), "1:01.5")

    def test_bpm_format_uses_chart_range(self):
        chart = Chart(
            [Tap(1000, lane=2, width=1), BpmChange(2000, 200, 4)],
            170,
            4,
        )
        self.assertEqual(_format_bpm(chart), "170–200")

    def test_page_cuts_land_on_beat_lines(self):
        context = RenderContext(Chart([Tap(5500, lane=2, width=1)], 120, 4))
        context.config.page_target_height = 1000

        self.assertEqual(_page_boundaries(context, 6000), [0, 2000, 4000, 6000])

    def test_extreme_track_speed_is_limited_for_preview_spacing(self):
        chart = Chart(
            [
                TrackSpeedChange(1000, 99999),
                TrackSpeedChange(1001, 1),
                Tap(2000, lane=2, width=1),
            ],
            120,
            4,
        )
        context = RenderContext(chart)

        self.assertEqual(context._raw_z_offset_for_time(1001), 1004)
        self.assertAlmostEqual(context.z_offset_for_time(2000), 721.08)

    def test_beat_lines_include_render_bounds(self):
        context = RenderContext(Chart([Tap(5500, lane=2, width=1)], 120, 4))

        self.assertEqual(
            _beat_line_timestamps_with_bounds(context, 6000),
            [0, 2000, 4000, 6000],
        )


if __name__ == "__main__":
    unittest.main()
