import unittest
from pathlib import Path

from if_chart.config import Config
from if_chart.renderer import _load_typeface


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

    def test_default_font_can_be_loaded(self):
        self.assertIsNotNone(_load_typeface(Config()))


if __name__ == "__main__":
    unittest.main()
