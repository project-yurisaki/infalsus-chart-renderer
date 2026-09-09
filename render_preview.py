import argparse
from pathlib import Path

from skia import EncodedImageFormat

from if_chart.parser import parse_chart
from if_chart.renderer import render


def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Render an In Falsus chart preview.")
    argument_parser.add_argument("chart", type=Path, help="Input .spc chart path")
    argument_parser.add_argument("output", type=Path, help="Output .png path")
    args = argument_parser.parse_args()

    chart = parse_chart(args.chart.read_text(encoding="utf-8"))
    image = render(chart, "", "", "")
    with args.output.open("wb") as output:
        image.save(output, EncodedImageFormat.kPNG)


if __name__ == "__main__":
    main()
