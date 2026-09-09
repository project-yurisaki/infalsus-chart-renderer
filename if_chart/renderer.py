from typing import TypeVar, Type
from parser import parse_chart
from elements import *
from config import Config
from skia import Surface, Canvas, Paint, Path, Image, EncodedImageFormat, Rect


class RenderContext:
    T = TypeVar('T')

    def __init__(self, chart: Chart) -> None:
        self.chart = chart
        self.raw_events = chart.events
        self.speed_changes = sorted([x for x in self.raw_events if isinstance(x, TrackSpeedChange)])
        self.bpm_changes = sorted([x for x in self.raw_events if isinstance(x, BpmChange)])
        self.config = Config()
        
    def _raw_z_offset_for_time(self, timestamp: int) -> float:
        speed = 1.0
        z = 0.0
        last_timestamp = 0
        for item in self.speed_changes:
            if last_timestamp >= timestamp:
                break
            if item.timestamp < timestamp:
                new_timestamp = min(item.timestamp, timestamp)
                z += (new_timestamp - last_timestamp) * speed
                # Use absolute speed here
                speed = abs(item.speed)
                last_timestamp = new_timestamp
            else:
                break
        if last_timestamp < timestamp:
            z += (timestamp - last_timestamp) * speed
        return z

    def get_objects_of_type(self, target_type: Type[T]) -> list[T]:
        return [x for x in self.raw_events if isinstance(x, target_type)]
    
    def z_offset_for_time(self, timestamp: int) -> float:
        return self._raw_z_offset_for_time(timestamp) * (self.config.pixels_per_sec / 1000)
    
    def get_max_object_time(self) -> int:
        return max(x.get_end_timestamp() for x in self.raw_events)

    def get_beat_line_timestamps(self) -> list[int]:
        res = []
        max_timestamp = self.get_max_object_time()
        last_timestamp = 0
        bpm, bpl = self.chart.bpm, self.chart.bpl
        for item in self.bpm_changes:
            interval = 1000 * bpl * 60 / bpm
            while last_timestamp + interval <= item.timestamp:
                last_timestamp = int(last_timestamp + interval)
                res.append(last_timestamp)
            if last_timestamp != item.timestamp:
                res.append(item.timestamp)
            last_timestamp = item.timestamp
            bpm, bpl = item.bpm, item.bpl
        interval = 1000 * bpl * 60 / bpm
        while last_timestamp + interval <= max_timestamp:
            last_timestamp = int(last_timestamp + interval)
            res.append(last_timestamp)
        return res


def render_lanes(ctx: RenderContext, canvas: Canvas):
    w = ctx.config.track_width / 6
    h = canvas.getSurface().height()
    colors = [0xDD302E43, 0xFF1B2A3A, 0xFF1B2A3A, 0xFF1B2A3A, 0xFF1B2A3A, 0xDD44223C]
    for i in range(6):
        canvas.drawRect(Rect(w * i, 0, w * (i + 1), h), Paint(Color=colors[i]))
    divider_colors = [0xFF535371, 0xFF535371, 0xFF01101C, 0xFF01101C, 0xFF01101C, 0xFF6C475B, 0xFF6C475B]
    for i in range(7):
        canvas.drawRect(Rect(w * i - 2, 0, w * i + 2, h), Paint(Color=divider_colors[i]))


def render_beat_lines(ctx: RenderContext, canvas: Canvas):
    timestamps = ctx.get_beat_line_timestamps()
    w = canvas.getSurface().width()
    for timestamp in timestamps:
        y = canvas.getSurface().height() - ctx.z_offset_for_time(timestamp)
        canvas.drawRect(Rect(0, y - 1, w, y), Paint(Color=0xFFFFFFFF))


def render_taps(ctx: RenderContext, canvas: Canvas):
    taps = ctx.get_objects_of_type(Tap)
    tap_image: Image = Image.open(ctx.config.tap_image_path)
    ratio = (ctx.config.track_width // 6 - 4) / tap_image.width()
    tap_image = tap_image.resize(int(tap_image.width() * ratio), int(tap_image.height() * ratio))
    for tap in taps:
        bottom = canvas.getSurface().height() - ctx.z_offset_for_time(tap.timestamp)
        left = ctx.config.track_width / 6 * tap.lane + 2
        top = bottom - tap_image.height()
        canvas.drawImage(tap_image, left, top)


def render(
    chart: Chart, jacket_path: str, title: str, artist: str
) -> Image:
    ctx = RenderContext(chart)
    track_height = int(ctx.z_offset_for_time(ctx.get_max_object_time() + 500))
    surface = Surface(ctx.config.track_width, track_height)
    canvas = surface.getCanvas()
    render_lanes(ctx, canvas)
    render_beat_lines(ctx, canvas)
    render_taps(ctx, canvas)
    return surface.makeImageSnapshot()


with open(r'D:\Dev\InFalsus\decrypted\ordirehv3.spc', 'r') as f:
    with open(r'D:\test.png', 'wb') as img:
        render(parse_chart(f.read()), '', '', '').save(img, EncodedImageFormat.kPNG)
