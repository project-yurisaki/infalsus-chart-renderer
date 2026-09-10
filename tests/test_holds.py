import unittest

from if_chart.elements import Chart, Hold
from if_chart.renderer import RenderContext, _hold_layout, _hold_tint_color


class HoldGeometryTests(unittest.TestCase):
    def test_width_extends_right_and_duration_controls_height(self):
        hold = Hold(100, lane=2, width=2, duration=500)
        context = RenderContext(Chart([hold], 120, 4))

        left, top, width, height = _hold_layout(context, hold, 1000)

        lane_width = context.config.track_width / 6
        self.assertEqual(left, lane_width * 2 + 2)
        self.assertEqual(top, 1000 - context.z_offset_for_time(600))
        self.assertEqual(width, int(lane_width * 2 - 4))
        self.assertEqual(
            height,
            round(
                context.z_offset_for_time(600)
                - context.z_offset_for_time(100)
            ),
        )

    def test_hold_tints(self):
        context = RenderContext(Chart([], 120, 4))

        self.assertEqual(
            _hold_tint_color(context, Hold(0, lane=0, width=1, duration=100)),
            context.config.tap_left_color,
        )
        self.assertEqual(
            _hold_tint_color(context, Hold(0, lane=5, width=1, duration=100)),
            context.config.tap_right_color,
        )
        self.assertEqual(
            _hold_tint_color(context, Hold(0, lane=2, width=2, duration=100)),
            context.config.hold_color,
        )


if __name__ == "__main__":
    unittest.main()
