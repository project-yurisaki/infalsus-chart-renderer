from math import cos, pi, sin
from typing import TypeVar, Type

from .elements import *
from .config import Config
from .notes import analyze_notes
from skia import (
    BlurStyle,
    BlendMode,
    Canvas,
    ColorFilters,
    Font,
    FontMgr,
    FontStyle,
    Image,
    MaskFilter,
    Paint,
    Path,
    Rect,
    Surface,
)


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
        res: list[float] = []
        max_timestamp = self.get_max_object_time()
        last_timestamp = 0.0
        bpm, bpl = self.chart.bpm, self.chart.bpl
        for item in self.bpm_changes:
            interval = 1000 * bpl * 60 / bpm
            while last_timestamp + interval <= item.timestamp:
                last_timestamp = last_timestamp + interval
                res.append(last_timestamp)
            if abs(last_timestamp - item.timestamp) >= 1:
                res.append(item.timestamp)
            last_timestamp = item.timestamp
            bpm, bpl = item.bpm, item.bpl
        interval = 1000 * bpl * 60 / bpm
        while last_timestamp + interval <= max_timestamp:
            last_timestamp = last_timestamp + interval
            res.append(last_timestamp)
        return list(map(int, res))


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


def _ease(progress: float, easing: int) -> float:
    """Apply skyarea easing: 0 straight, 1 sine-out, 2 sine-in."""
    if easing == 1:
        return sin(progress * pi / 2)
    if easing == 2:
        return 1.0 - cos(progress * pi / 2)
    return progress


def _skyarea_points(
    ctx: RenderContext, skyarea: SkyArea, surface_height: int
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return sampled left and right boundaries, ordered start to end."""
    start_left = skyarea.start_x - skyarea.start_width / 2
    start_right = skyarea.start_x + skyarea.start_width / 2
    end_left = skyarea.end_x - skyarea.end_width / 2
    end_right = skyarea.end_x + skyarea.end_width / 2

    height = abs(
        ctx.z_offset_for_time(skyarea.timestamp + skyarea.duration)
        - ctx.z_offset_for_time(skyarea.timestamp)
    )
    # Curves are sampled often enough to stay smooth without making long,
    # straight skyareas unnecessarily expensive.
    sample_count = max(1, int(height / 8))
    left_points = []
    right_points = []
    for index in range(sample_count + 1):
        progress = index / sample_count
        timestamp = skyarea.timestamp + skyarea.duration * progress
        y = surface_height - ctx.z_offset_for_time(timestamp)
        left_x = (start_left + (end_left - start_left) * _ease(progress, skyarea.easing_left)) * ctx.config.track_width
        right_x = (start_right + (end_right - start_right) * _ease(progress, skyarea.easing_right)) * ctx.config.track_width
        left_points.append((left_x, y))
        right_points.append((right_x, y))
    return left_points, right_points


def _path_from_points(points: list[tuple[float, float]]) -> Path:
    path = Path()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    return path


def render_skyareas(ctx: RenderContext, canvas: Canvas):
    skyareas = ctx.get_objects_of_type(SkyArea)
    if not skyareas:
        return

    surface_height = canvas.getSurface().height()
    by_group = {}
    for skyarea in skyareas:
        by_group.setdefault(skyarea.group_id, []).append(skyarea)

    fill_paint = Paint(Color=ctx.config.skyarea_fill_color, AntiAlias=True)
    fill_paint.setBlendMode(BlendMode.kSrcOver)
    glow_paint = Paint(
        Color=ctx.config.skyarea_edge_glow_color,
        AntiAlias=True,
        Style=Paint.kStroke_Style,
        StrokeWidth=ctx.config.skyarea_edge_glow_width,
    )
    glow_paint.setMaskFilter(
        MaskFilter.MakeBlur(
            BlurStyle.kNormal_BlurStyle,
            ctx.config.skyarea_edge_glow_blur,
        )
    )
    edge_paint = Paint(
        Color=ctx.config.skyarea_edge_color,
        AntiAlias=True,
        Style=Paint.kStroke_Style,
        StrokeWidth=ctx.config.skyarea_edge_width,
    )

    for group in by_group.values():
        group.sort()
        for index, skyarea in enumerate(group):
            left_points, right_points = _skyarea_points(ctx, skyarea, surface_height)
            has_previous = (
                index > 0
                and abs(skyarea.timestamp - group[index - 1].get_end_timestamp()) <= 2
            )
            has_next = (
                index < len(group) - 1
                and abs(group[index + 1].timestamp - skyarea.get_end_timestamp()) <= 2
            )

            area_path = _path_from_points(left_points)
            for point in reversed(right_points):
                area_path.lineTo(*point)
            area_path.close()
            canvas.drawPath(area_path, fill_paint)

            # Side edges are always visible. Horizontal caps are only drawn at
            # the outer ends of a continuous group, avoiding seams between its
            # component commands.
            edge_paths = [
                _path_from_points(left_points),
                _path_from_points(right_points),
            ]
            if not has_previous:
                edge_paths.append(_path_from_points([left_points[0], right_points[0]]))
            if not has_next:
                edge_paths.append(_path_from_points([left_points[-1], right_points[-1]]))

            for edge_path in edge_paths:
                canvas.drawPath(edge_path, glow_paint)
                canvas.drawPath(edge_path, edge_paint)


def _get_tint_paint(cache: dict[int, Paint], color: int) -> Paint:
    paint = cache.get(color)
    if paint is None:
        paint = Paint(AntiAlias=True)
        paint.setColorFilter(ColorFilters.Blend(color, BlendMode.kColor))
        cache[color] = paint
    return paint


def render_holds(ctx: RenderContext, canvas: Canvas):
    holds = ctx.get_objects_of_type(Hold)
    if not holds:
        return

    source_image: Image = Image.open(ctx.config.hold_image_path)
    resized_images = {}
    tint_paints = {}
    surface_height = canvas.getSurface().height()
    for hold in holds:
        left, top, width, height = _hold_layout(ctx, hold, surface_height)
        size = (width, height)
        hold_image = resized_images.get(size)
        if hold_image is None:
            hold_image = source_image.resize(width, height)
            resized_images[size] = hold_image
        paint = _get_tint_paint(tint_paints, _hold_tint_color(ctx, hold))
        canvas.drawImage(hold_image, left, top, paint=paint)


def _hold_layout(
    ctx: RenderContext, hold: Hold, surface_height: int
) -> tuple[float, float, int, int]:
    """Return left, top, width and height for a ground hold."""
    lane_width = ctx.config.track_width / 6
    left = lane_width * hold.lane + 2
    width = max(1, int(lane_width * hold.width - 4))
    bottom = surface_height - ctx.z_offset_for_time(hold.timestamp)
    top = surface_height - ctx.z_offset_for_time(hold.get_end_timestamp())
    height = max(1, int(round(bottom - top)))
    return left, top, width, height


def _hold_tint_color(ctx: RenderContext, hold: Hold) -> int:
    if hold.lane <= 0:
        return ctx.config.tap_left_color
    if hold.lane + hold.width >= 6:
        return ctx.config.tap_right_color
    return ctx.config.hold_color


def render_taps(ctx: RenderContext, canvas: Canvas):
    taps = ctx.get_objects_of_type(Tap)
    source_image: Image = Image.open(ctx.config.tap_image_path)
    resized_images = {}
    tint_paints = {}
    for tap in taps:
        left, width, height = _tap_layout(
            ctx, tap, source_image.width(), source_image.height()
        )
        tap_image = resized_images.get(tap.width)
        if tap_image is None:
            tap_image = source_image.resize(width, height)
            resized_images[tap.width] = tap_image
        bottom = canvas.getSurface().height() - ctx.z_offset_for_time(tap.timestamp)
        top = bottom - tap_image.height()
        tint_color = _tap_tint_color(ctx, tap)
        paint = _get_tint_paint(tint_paints, tint_color)
        canvas.drawImage(tap_image, left, top, paint=paint)


def _tap_layout(
    ctx: RenderContext, tap: Tap, source_width: int, source_height: int
) -> tuple[float, int, int]:
    """Return left, width and height for a right-extending tap."""
    lane_width = ctx.config.track_width / 6
    single_lane_width = lane_width - 4
    height = max(1, int(source_height * single_lane_width / source_width))
    width = max(1, int(lane_width * tap.width - 4))
    left = lane_width * tap.lane + 2
    return left, width, height


def _tap_tint_color(ctx: RenderContext, tap: Tap) -> int:
    """Return the side-lane tint for a tap, with the left side taking priority."""
    if tap.lane <= 0:
        return ctx.config.tap_left_color
    if tap.lane + tap.width >= 6:
        return ctx.config.tap_right_color
    return ctx.config.tap_color


def _directional_flick_path(
    ctx: RenderContext, flick: DirectionalFlick, surface_height: int
) -> tuple[Path, Path]:
    """Return the filled body and highlighted leading edge of a flick."""
    width = flick.width * ctx.config.track_width
    left = (flick.x - flick.width / 2) * ctx.config.track_width
    right = left + width
    base_y = surface_height - ctx.z_offset_for_time(flick.timestamp)
    height = ctx.config.directional_flick_height

    # Direction 4 points right and direction 16 points left. Build the right
    # shape first, then mirror its x coordinates for the left variant.
    def x(value: float) -> float:
        position = left + value * width
        return left + right - position if flick.direction == 0x10 else position

    tip_x = x(0.72)
    tip_y = base_y - height
    body = Path()
    body.moveTo(x(0.0), base_y)
    body.cubicTo(
        x(0.22), base_y - height * 0.08,
        x(0.58), base_y - height * 0.58,
        tip_x, tip_y,
    )
    body.cubicTo(
        x(0.80), base_y - height * 0.62,
        x(0.93), base_y - height * 0.16,
        x(1.0), base_y,
    )
    body.close()

    leading_edge = Path()
    leading_edge.moveTo(tip_x, tip_y)
    leading_edge.cubicTo(
        x(0.80), base_y - height * 0.62,
        x(0.93), base_y - height * 0.16,
        x(1.0), base_y,
    )
    return body, leading_edge


def _directional_flick_color(ctx: RenderContext, flick: DirectionalFlick) -> int:
    if flick.direction == 0x10:
        return ctx.config.directional_flick_left_color
    return ctx.config.directional_flick_right_color


def render_directional_flicks(ctx: RenderContext, canvas: Canvas):
    flicks = ctx.get_objects_of_type(DirectionalFlick)
    if not flicks:
        return

    surface_height = canvas.getSurface().height()
    paints = {}
    for flick in flicks:
        color = _directional_flick_color(ctx, flick)
        if color not in paints:
            opaque_color = 0xFF000000 | (color & 0x00FFFFFF)
            fill_paint = Paint(Color=color, AntiAlias=True)
            glow_paint = Paint(
                Color=color,
                AntiAlias=True,
                Style=Paint.kStroke_Style,
                StrokeWidth=ctx.config.directional_flick_edge_width * 2,
            )
            glow_paint.setMaskFilter(
                MaskFilter.MakeBlur(
                    BlurStyle.kNormal_BlurStyle,
                    ctx.config.directional_flick_glow_blur,
                )
            )
            edge_paint = Paint(
                Color=opaque_color,
                AntiAlias=True,
                Style=Paint.kStroke_Style,
                StrokeWidth=ctx.config.directional_flick_edge_width,
            )
            paints[color] = (fill_paint, glow_paint, edge_paint)

        fill_paint, glow_paint, edge_paint = paints[color]
        body, leading_edge = _directional_flick_path(ctx, flick, surface_height)
        canvas.drawPath(body, fill_paint)
        canvas.drawPath(leading_edge, glow_paint)
        canvas.drawPath(leading_edge, edge_paint)


def _format_chart_time(timestamp: int) -> str:
    total_tenths = int(timestamp / 100 + 0.5)
    minutes, remainder = divmod(total_tenths, 600)
    seconds, tenths = divmod(remainder, 10)
    return f"{minutes}:{seconds:02d}.{tenths}"


def _page_boundaries(ctx: RenderContext, end_timestamp: int) -> list[int]:
    """Split near the target height, using beat lines as measure-safe cuts."""
    target_height = ctx.config.page_target_height
    end_z = ctx.z_offset_for_time(end_timestamp)
    beat_lines = [
        (timestamp, ctx.z_offset_for_time(timestamp))
        for timestamp in ctx.get_beat_line_timestamps()
        if 0 < timestamp < end_timestamp
    ]
    boundaries = [0]
    current_timestamp = 0
    current_z = 0.0

    while end_z - current_z > target_height:
        eligible = [
            item
            for item in beat_lines
            if item[0] > current_timestamp and item[1] - current_z <= target_height
        ]
        if eligible:
            next_timestamp, next_z = eligible[-1]
        else:
            remaining = [item for item in beat_lines if item[0] > current_timestamp]
            if not remaining:
                break
            next_timestamp, next_z = remaining[0]

        boundaries.append(next_timestamp)
        current_timestamp = next_timestamp
        current_z = next_z

    boundaries.append(end_timestamp)
    return boundaries


def _render_track(ctx: RenderContext, end_timestamp: int) -> Image:
    track_height = int(ctx.z_offset_for_time(end_timestamp))
    surface = Surface(ctx.config.track_width, track_height)
    canvas = surface.getCanvas()
    render_lanes(ctx, canvas)
    render_beat_lines(ctx, canvas)
    render_holds(ctx, canvas)
    render_taps(ctx, canvas)
    render_skyareas(ctx, canvas)
    render_directional_flicks(ctx, canvas)
    return surface.makeImageSnapshot()


def _render_pages(
    ctx: RenderContext, track_image: Image, boundaries: list[int]
) -> Image:
    config = ctx.config
    page_count = len(boundaries) - 1
    boundary_offsets = [
        int(round(ctx.z_offset_for_time(timestamp)))
        for timestamp in boundaries[:-1]
    ] + [track_image.height()]
    slice_heights = [
        end - start
        for start, end in zip(boundary_offsets, boundary_offsets[1:])
    ]
    page_height = max(config.page_target_height, max(slice_heights))
    page_width = (
        config.page_time_column_width
        + config.track_width
        + config.page_rhythm_column_width
    )
    total_width = (
        config.page_padding * 2
        + page_count * page_width
        + (page_count - 1) * config.page_gap
    )
    total_height = config.page_padding * 2 + page_height + config.footer_height

    surface = Surface(total_width, total_height)
    canvas = surface.getCanvas()
    canvas.clear(config.page_background_color)

    typeface = FontMgr.RefDefault().matchFamilyStyle("Arial", FontStyle())
    font = Font(typeface, config.page_time_font_size)
    time_paint = Paint(Color=config.page_time_color, AntiAlias=True)
    rhythm_font = Font(typeface, config.page_rhythm_font_size)
    rhythm_paint = Paint(Color=config.page_rhythm_color, AntiAlias=True)
    beat_lines = ctx.get_beat_line_timestamps()
    analyzed_notes = analyze_notes(ctx.chart)

    for page_index in range(page_count):
        start_timestamp = boundaries[page_index]
        end_timestamp = boundaries[page_index + 1]
        start_offset = boundary_offsets[page_index]
        end_offset = boundary_offsets[page_index + 1]
        slice_height = slice_heights[page_index]
        page_left = config.page_padding + page_index * (page_width + config.page_gap)
        track_left = page_left + config.page_time_column_width
        page_bottom = config.page_padding + page_height
        page_top = page_bottom - slice_height

        source_top = track_image.height() - end_offset
        source_bottom = track_image.height() - start_offset
        canvas.drawImageRect(
            track_image,
            Rect(0, source_top, config.track_width, source_bottom),
            Rect(track_left, page_top, track_left + config.track_width, page_bottom),
        )

        start_z = ctx.z_offset_for_time(start_timestamp)
        for timestamp in beat_lines:
            if not (start_timestamp < timestamp <= end_timestamp):
                continue
            y = page_bottom - (ctx.z_offset_for_time(timestamp) - start_z)
            label = _format_chart_time(timestamp)
            label_width = font.measureText(label, paint=time_paint)
            x = track_left - config.page_time_label_gap - label_width
            canvas.drawString(
                label,
                x,
                y + config.page_time_font_size * 0.35,
                font,
                time_paint,
            )

        rhythm_x = (
            track_left
            + config.track_width
            + config.page_rhythm_label_gap
        )
        for note in analyzed_notes:
            if not note.display:
                continue
            if page_index == 0:
                is_on_page = start_timestamp <= note.time_point <= end_timestamp
            else:
                is_on_page = start_timestamp < note.time_point <= end_timestamp
            if not is_on_page:
                continue
            y = page_bottom - (
                ctx.z_offset_for_time(note.time_point) - start_z
            )
            canvas.drawString(
                note.display,
                rhythm_x,
                y + config.page_rhythm_font_size * 0.35,
                rhythm_font,
                rhythm_paint,
            )

    return surface.makeImageSnapshot()


def render(
    chart: Chart, jacket_path: str, title: str, artist: str
) -> Image:
    ctx = RenderContext(chart)
    end_timestamp = ctx.get_max_object_time() + 500
    track_image = _render_track(ctx, end_timestamp)
    boundaries = _page_boundaries(ctx, end_timestamp)
    return _render_pages(ctx, track_image, boundaries)
