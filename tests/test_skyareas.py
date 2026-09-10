import unittest

from if_chart.elements import Chart, SkyArea, Tap
from if_chart.parser import parse_chart
from if_chart.renderer import (
    RenderContext,
    _ease,
    _skyarea_points,
    _tap_layout,
    _tap_tint_color,
)


class SkyAreaParserTests(unittest.TestCase):
    def test_skyarea_can_touch_track_edge(self):
        chart = parse_chart("skyarea(0,2,12,4,10,12,4,0,0,100)")

        self.assertEqual(len(chart.events), 1)
        self.assertAlmostEqual(chart.events[0].start_x - chart.events[0].start_width / 2, 0)
        self.assertAlmostEqual(chart.events[0].end_x + chart.events[0].end_width / 2, 1)

    def test_contiguous_implicit_skyareas_share_group(self):
        chart = parse_chart(
            "skyarea(0,6,12,4,6,12,4,0,0,100)\n"
            "skyarea(100,6,12,4,6,12,4,0,0,100)"
        )

        self.assertEqual(chart.events[0].group_id, chart.events[1].group_id)


class SkyAreaGeometryTests(unittest.TestCase):
    def test_easing_curves(self):
        self.assertEqual(_ease(0.5, 0), 0.5)
        self.assertAlmostEqual(_ease(0.5, 1), 0.7071067811865475)
        self.assertAlmostEqual(_ease(0.5, 2), 0.2928932188134524)

    def test_points_use_normalized_track_coordinates(self):
        skyarea = SkyArea(0, 0.5, 0.5, 0.5, 0.25, 0, 0, 100, 1)
        context = RenderContext(Chart([skyarea], 120, 4))

        left, right = _skyarea_points(context, skyarea, 1000)

        track_width = context.config.track_width
        self.assertEqual(left[0], (track_width * 0.25, 1000))
        self.assertEqual(right[0], (track_width * 0.75, 1000))
        end_y = 1000 - context.z_offset_for_time(100)
        self.assertEqual(left[-1], (track_width * 0.375, end_y))
        self.assertEqual(right[-1], (track_width * 0.625, end_y))


class TapGeometryTests(unittest.TestCase):
    def test_width_extends_right_without_changing_height(self):
        tap = Tap(0, lane=2, width=3)
        context = RenderContext(Chart([tap], 120, 4))

        left, width, height = _tap_layout(context, tap, 247, 61)

        lane_width = context.config.track_width / 6
        self.assertEqual(left, lane_width * 2 + 2)
        self.assertEqual(width, int(lane_width * 3 - 4))
        self.assertEqual(height, int(61 * (lane_width - 4) / 247))

    def test_side_lane_tints(self):
        context = RenderContext(Chart([], 120, 4))

        self.assertEqual(
            _tap_tint_color(context, Tap(0, lane=0, width=1)),
            context.config.tap_left_color,
        )
        self.assertEqual(
            _tap_tint_color(context, Tap(0, lane=5, width=1)),
            context.config.tap_right_color,
        )
        self.assertEqual(
            _tap_tint_color(context, Tap(0, lane=2, width=1)),
            context.config.tap_color,
        )


if __name__ == "__main__":
    unittest.main()
