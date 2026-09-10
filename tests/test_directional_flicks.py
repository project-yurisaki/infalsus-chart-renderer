import unittest

from if_chart.elements import Chart, DirectionalFlick
from if_chart.parser import parse_chart
from if_chart.renderer import (
    RenderContext,
    _directional_flick_color,
    _directional_flick_path,
    _directional_flick_tail_factor,
    _directional_flick_tip_x,
)


class DirectionalFlickParserTests(unittest.TestCase):
    def test_chart_direction_values_are_accepted(self):
        chart = parse_chart(
            "flick(100,6,12,4,4)\n"
            "flick(200,6,12,4,16)"
        )

        self.assertEqual([event.direction for event in chart.events], [4, 16])


class DirectionalFlickGeometryTests(unittest.TestCase):
    def test_direction_colors(self):
        context = RenderContext(Chart([], 120, 4))

        self.assertEqual(
            _directional_flick_color(context, DirectionalFlick(0, 0.5, 0.25, 4)),
            context.config.directional_flick_right_color,
        )
        self.assertEqual(
            _directional_flick_color(context, DirectionalFlick(0, 0.5, 0.25, 16)),
            context.config.directional_flick_left_color,
        )

    def test_left_and_right_paths_share_bounds(self):
        context = RenderContext(Chart([], 120, 4))
        right, _, _ = _directional_flick_path(
            context, DirectionalFlick(0, 0.5, 0.25, 4), 1000
        )
        left, _, _ = _directional_flick_path(
            context, DirectionalFlick(0, 0.5, 0.25, 16), 1000
        )

        self.assertEqual(right.computeTightBounds(), left.computeTightBounds())

    def test_tip_uses_fixed_inset_for_long_flicks(self):
        context = RenderContext(Chart([], 120, 4))
        short = DirectionalFlick(0, 0.25, 0.25, 4)
        long = DirectionalFlick(0, 0.5, 0.75, 4)

        short_right = (short.x + short.width / 2) * context.config.track_width
        long_right = (long.x + long.width / 2) * context.config.track_width

        self.assertEqual(
            short_right - _directional_flick_tip_x(context, short),
            context.config.directional_flick_tip_inset,
        )
        self.assertEqual(
            long_right - _directional_flick_tip_x(context, long),
            context.config.directional_flick_tip_inset,
        )

    def test_tail_uses_hyperbolic_falloff(self):
        self.assertEqual(_directional_flick_tail_factor(0, 120, 80), 1)
        self.assertAlmostEqual(
            _directional_flick_tail_factor(60, 120, 80),
            2 / 7,
        )
        self.assertEqual(_directional_flick_tail_factor(120, 120, 80), 0)

    def test_long_tail_falls_closer_to_baseline_at_its_midpoint(self):
        short_midpoint = _directional_flick_tail_factor(60, 120, 80)
        long_midpoint = _directional_flick_tail_factor(200, 400, 80)

        self.assertLess(long_midpoint, short_midpoint)


if __name__ == "__main__":
    unittest.main()
