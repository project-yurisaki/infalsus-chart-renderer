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

import argparse
from pathlib import Path

from skia import EncodedImageFormat

from if_chart.parser import parse_chart
from if_chart.renderer import render


def create_argument_parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description="Render an In Falsus chart preview.")
    argument_parser.add_argument("chart", type=Path, help="Input .spc chart path")
    argument_parser.add_argument("output", type=Path, help="Output .jpg path")
    argument_parser.add_argument("--font", type=Path, help="Custom font file")
    argument_parser.add_argument("--jacket", type=Path, help="Square jacket image")
    argument_parser.add_argument("--title", default="", help="Song title")
    argument_parser.add_argument("--artist", default="", help="Song artist")
    argument_parser.add_argument(
        "--chart-designer", default="", help="Chart designer"
    )
    argument_parser.add_argument(
        "--jacket-designer", default="", help="Jacket designer"
    )
    argument_parser.add_argument("--level", default="", help="Chart level")
    return argument_parser


def main() -> None:
    args = create_argument_parser().parse_args()

    chart = parse_chart(args.chart.read_text(encoding="utf-8"))
    image = render(
        chart,
        str(args.jacket) if args.jacket else "",
        args.title,
        args.artist,
        chart_designer=args.chart_designer,
        jacket_designer=args.jacket_designer,
        level=args.level,
        font_path=str(args.font) if args.font else "",
    )
    with args.output.open("wb") as output:
        image.save(output, EncodedImageFormat.kJPEG, quality=90)


if __name__ == "__main__":
    main()
