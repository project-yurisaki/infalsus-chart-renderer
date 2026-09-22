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
from pathlib import Path
from unittest.mock import patch

from if_chart.elements import Chart, Tap
from if_chart.config import Config
from if_chart.renderer import _load_typeface, render
from render_preview import create_argument_parser


class BuiltinAssetTests(unittest.TestCase):
    def test_default_assets_are_packaged_under_if_chart(self):
        for resource_path in (
            Config.font_path,
            Config.tap_image_path,
            Config.hold_image_path,
        ):
            path = Path(resource_path)
            self.assertTrue(path.is_file())
            self.assertEqual(path.parent.name, "assets")
            self.assertEqual(path.parent.parent.name, "if_chart")

        self.assertEqual(Path(Config.tap_image_path).name, "note.png")
        self.assertEqual(Path(Config.hold_image_path).name, "note_hold.png")

    def test_default_font_can_be_loaded(self):
        self.assertIsNotNone(_load_typeface(Config()))

    def test_cli_accepts_custom_font(self):
        args = create_argument_parser().parse_args(
            ["chart.spc", "output.jpg", "--font", "custom.ttf"]
        )
        self.assertEqual(args.font, Path("custom.ttf"))

    def test_render_uses_custom_font(self):
        custom_font = Config.font_path
        config = Config()
        config.font_path = custom_font
        chart = Chart([Tap(1000, lane=2, width=1)], 120, 4)
        with patch.object(Config, "font_path", "missing-font.ttf"):
            image = render(chart, "", "Title", "Artist", config=config)
        self.assertGreater(image.width(), 0)
        self.assertGreater(image.height(), 0)


if __name__ == "__main__":
    unittest.main()
