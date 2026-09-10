import argparse
from pathlib import Path

from skia import EncodedImageFormat

from if_chart.parser import parse_chart
from if_chart.renderer import render


def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Render an In Falsus chart preview.")
    argument_parser.add_argument("chart", type=Path, help="Input .spc chart path")
    argument_parser.add_argument("output", type=Path, help="Output .jpg path")
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
    args = argument_parser.parse_args()

    chart = parse_chart(args.chart.read_text(encoding="utf-8"))
    image = render(
        chart,
        str(args.jacket) if args.jacket else "",
        args.title,
        args.artist,
        chart_designer=args.chart_designer,
        jacket_designer=args.jacket_designer,
        level=args.level,
    )
    with args.output.open("wb") as output:
        image.save(output, EncodedImageFormat.kJPEG, quality=90)


if __name__ == "__main__":
    main()
