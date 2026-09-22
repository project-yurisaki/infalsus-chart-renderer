# In Falsus Chart Renderer

![Yurisaki SubProject](https://img.shields.io/badge/SubProject-Yurisaki-A5D8FF?style=for-the-badge)
![SLanguage Python](https://img.shields.io/badge/Language-Python-blue?style=for-the-badge)


A flat preview image generator for In Falsus charts, implemented with Python and Skia.

## Requirements

- Python 3.10 or later
- Windows, Linux, or macOS

## Installation

Clone or download the project, then install its dependencies from the project directory:

```shell
python -m pip install -r requirements.txt
```

The default font and note textures are bundled with the project, so no additional assets are required.

## Command-line usage

> [!IMPORTANT]
> The input `.spc` file must be a decrypted, text-format chart. Encrypted or binary `.spc` files are not supported.

To generate a preview with the default options:

```shell
python render_preview.py path/to/chart.spc preview.jpg
```

To include a jacket and chart metadata:

```shell
python render_preview.py path/to/chart.spc preview.jpg \
  --jacket path/to/jacket.png \
  --title "Song Title" \
  --artist "Artist" \
  --chart-designer "Chart Designer" \
  --jacket-designer "Jacket Designer" \
  --level "12+"
```

The same command can be written on one line in PowerShell:

```powershell
python render_preview.py "D:\Charts\example.spc" "preview.jpg" --jacket "D:\Charts\jacket.png" --title "Song Title" --artist "Artist" --chart-designer "Chart Designer" --jacket-designer "Jacket Designer" --level "12+"
```

Available arguments:

| Argument | Description |
| --- | --- |
| `chart` | Path to a decrypted, text-format `.spc` chart |
| `output` | Path to the output JPEG image |
| `--font` | Optional custom font file; the bundled font is used when omitted |
| `--jacket` | Optional jacket image; it is center-cropped to a square |
| `--title` | Song title |
| `--artist` | Song artist |
| `--chart-designer` | Chart designer |
| `--jacket-designer` | Jacket designer |
| `--level` | Chart level |

`render_preview.py` currently always encodes the result as a quality-90 JPEG. Use a
`.jpg` or `.jpeg` extension for the output file.

To display the complete command help:

```shell
python render_preview.py --help
```

## Python API

Charts can also be parsed and rendered directly from Python:

```python
from pathlib import Path

from skia import EncodedImageFormat

from if_chart.config import Config
from if_chart.parser import parse_chart
from if_chart.renderer import render


chart = parse_chart(Path("chart.spc").read_text(encoding="utf-8"))
config = Config()
config.max_visual_track_speed = 4.0
# config.font_path = "custom-font.ttf"

image = render(
    chart,
    jacket_path="jacket.png",
    title="Song Title",
    artist="Artist",
    chart_designer="Chart Designer",
    jacket_designer="Jacket Designer",
    level="12+",
    config=config,
)

with Path("preview.jpg").open("wb") as output:
    image.save(output, EncodedImageFormat.kJPEG, quality=90)
```

Pass a `Config` instance to `render()` to customize rendering dimensions,
colors, the visual track-speed limit, and other options. To use a custom
font, set `config.font_path` before calling `render()`.

## Third-party assets

The bundled `note.png` and `note_hold.png` textures come from
[Arcaea-Infinity/OpenArcaeaArts](https://github.com/Arcaea-Infinity/OpenArcaeaArts).
They are licensed under CC BY-NC 4.0 and are restricted to non-commercial use.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution,
modification details, and the bundled license text.
