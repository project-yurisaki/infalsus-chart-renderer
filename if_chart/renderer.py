from dataclasses import dataclass
from math import cos, pi, sin
import os
from typing import TypeVar, Type

from .elements import *
from .config import Config
from .note_judgement import get_chart_judgement_points, get_combo_before
from .notes import analyze_notes
from skia import (
    BlurStyle,
    BlendMode,
    Canvas,
    ColorFilters,
    Font,
    Image,
    MaskFilter,
    Paint,
    Path,
    Rect,
    Surface,
    Typeface,
)


@dataclass(frozen=True)
class RenderMetadata:
    jacket_path: str
    title: str
    artist: str
    chart_designer: str = ""
    jacket_designer: str = ""
    level: str = ""


class RenderContext:
    T = TypeVar('T')

    def __init__(self, chart: Chart) -> None:
        self.chart = chart
        self.raw_events = chart.events
        self.speed_changes = sorted([x for x in self.raw_events if isinstance(x, TrackSpeedChange)])
        self.bpm_changes = sorted([x for x in self.raw_events if isinstance(x, BpmChange)])
        self.config = Config()

    def _visual_track_speed(self, speed: float) -> float:
        speed = abs(speed)
        limit = self.config.max_visual_track_speed
        if limit <= 0:
            return speed
        return min(speed, limit)
        
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
                speed = self._visual_track_speed(item.speed)
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


def _load_typeface(config: Config) -> Typeface:
    typeface = Typeface.MakeFromFile(config.font_path)
    if typeface is None:
        raise RuntimeError(f"Unable to load font: {config.font_path}")
    return typeface


def render_lanes(ctx: RenderContext, canvas: Canvas):
    w = ctx.config.track_width / 6
    h = canvas.getSurface().height()
    colors = [0xDD302E43, 0xFF1B2A3A, 0xFF1B2A3A, 0xFF1B2A3A, 0xFF1B2A3A, 0xDD44223C]
    for i in range(6):
        canvas.drawRect(Rect(w * i, 0, w * (i + 1), h), Paint(Color=colors[i]))
    divider_colors = [0xFF535371, 0xFF535371, 0xFF01101C, 0xFF01101C, 0xFF01101C, 0xFF6C475B, 0xFF6C475B]
    for i in range(7):
        canvas.drawRect(Rect(w * i - 2, 0, w * i + 2, h), Paint(Color=divider_colors[i]))


def _beat_line_timestamps_with_bounds(
    ctx: RenderContext, end_timestamp: int
) -> list[int]:
    return sorted({
        0,
        end_timestamp,
        *(
            timestamp
            for timestamp in ctx.get_beat_line_timestamps()
            if 0 < timestamp < end_timestamp
        ),
    })


def render_beat_lines(
    ctx: RenderContext, canvas: Canvas, end_timestamp: int
):
    timestamps = _beat_line_timestamps_with_bounds(ctx, end_timestamp)
    w = canvas.getSurface().width()
    h = canvas.getSurface().height()
    for timestamp in timestamps:
        y = h - ctx.z_offset_for_time(timestamp)
        line_top = min(max(y - 1, 0), h - 1)
        canvas.drawRect(
            Rect(0, line_top, w, line_top + 1),
            Paint(Color=0xFFFFFFFF),
        )


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
        prev_left_points = None
        prev_right_points = None
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
            else:
                # If widths are unequal, draw connecting lines between endpoints
                if prev_left_points is not None and prev_right_points is not None:
                    # Check if left endpoints don't match
                    if abs(prev_left_points[-1][0] - left_points[0][0]) > 0.01:
                        edge_paths.append(_path_from_points([prev_left_points[-1], left_points[0]]))
                    # Check if right endpoints don't match
                    if abs(prev_right_points[-1][0] - right_points[0][0]) > 0.01:
                        edge_paths.append(_path_from_points([prev_right_points[-1], right_points[0]]))
            if not has_next:
                edge_paths.append(_path_from_points([left_points[-1], right_points[-1]]))

            for edge_path in edge_paths:
                canvas.drawPath(edge_path, glow_paint)
                canvas.drawPath(edge_path, edge_paint)
            
            prev_left_points = left_points
            prev_right_points = right_points


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


def _directional_flick_tail_factor(
    distance_from_tip: float, tail_length: float, scale: float
) -> float:
    """Reciprocal falloff normalized to one at the tip and zero at the tail."""
    if tail_length <= 0:
        return 0.0
    end_value = scale / (tail_length + scale)
    value = scale / (distance_from_tip + scale)
    return (value - end_value) / (1.0 - end_value)


def _directional_flick_path(
    ctx: RenderContext, flick: DirectionalFlick, surface_height: int
) -> tuple[Path, Path, Path]:
    """Return the filled body, leading edge and full-width baseline."""
    width = flick.width * ctx.config.track_width
    left = (flick.x - flick.width / 2) * ctx.config.track_width
    right = left + width
    base_y = surface_height - ctx.z_offset_for_time(flick.timestamp)
    height = ctx.config.directional_flick_height
    tip_inset = min(ctx.config.directional_flick_tip_inset, width * 0.45)

    # Distances are measured back from the direction-facing edge. The tip keeps
    # a fixed inset, while the trailing edge follows a normalized hyperbola.
    def x(distance_from_leading_edge: float) -> float:
        distance = min(distance_from_leading_edge, width)
        if flick.direction == 0x10:
            return left + distance
        return right - distance

    tip_x = x(tip_inset)
    tip_y = base_y - height
    tail_length = width - tip_inset
    sample_count = max(2, int(tail_length / 8))
    body = Path()
    body.moveTo(x(width), base_y)
    for index in range(1, sample_count + 1):
        progress = index / sample_count
        distance_ratio = 1.0 - progress
        distance = tip_inset + tail_length * distance_ratio
        height_factor = _directional_flick_tail_factor(
            tail_length * distance_ratio,
            tail_length,
            ctx.config.directional_flick_tail_scale,
        )
        body.lineTo(x(distance), base_y - height * height_factor)
    body.cubicTo(
        x(tip_inset * 0.65), base_y - height * 0.62,
        x(tip_inset * 0.15), base_y - height * 0.16,
        x(0.0), base_y,
    )
    body.close()

    leading_edge = Path()
    leading_edge.moveTo(tip_x, tip_y)
    leading_edge.cubicTo(
        x(tip_inset * 0.65), base_y - height * 0.62,
        x(tip_inset * 0.15), base_y - height * 0.16,
        x(0.0), base_y,
    )
    baseline = Path()
    baseline.moveTo(left, base_y)
    baseline.lineTo(right, base_y)
    return body, leading_edge, baseline


def _directional_flick_tip_x(ctx: RenderContext, flick: DirectionalFlick) -> float:
    width = flick.width * ctx.config.track_width
    left = (flick.x - flick.width / 2) * ctx.config.track_width
    inset = min(ctx.config.directional_flick_tip_inset, width * 0.45)
    if flick.direction == 0x10:
        return left + inset
    return left + width - inset


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
        body, leading_edge, baseline = _directional_flick_path(
            ctx, flick, surface_height
        )
        canvas.drawPath(body, fill_paint)
        canvas.drawPath(baseline, glow_paint)
        canvas.drawPath(baseline, edge_paint)
        canvas.drawPath(leading_edge, glow_paint)
        canvas.drawPath(leading_edge, edge_paint)


def _format_chart_time(timestamp: int) -> str:
    total_tenths = int(timestamp / 100 + 0.5)
    minutes, remainder = divmod(total_tenths, 600)
    seconds, tenths = divmod(remainder, 10)
    return f"{minutes}:{seconds:02d}.{tenths}"


def _format_bpm(chart: Chart) -> str:
    bpm_values = {float(chart.bpm)}
    bpm_values.update(
        float(event.bpm)
        for event in chart.events
        if isinstance(event, BpmChange)
    )
    minimum = min(bpm_values)
    maximum = max(bpm_values)
    if minimum == maximum:
        return f"{minimum:g}"
    return f"{minimum:g}–{maximum:g}"


def _footer_min_width(config: Config) -> int:
    return (
        config.footer_padding * 2
        + config.footer_jacket_size
        + config.footer_jacket_gap
        + config.footer_identity_width
        + config.footer_section_gap
        + config.footer_count_width
        + config.footer_section_gap
        + config.footer_detail_width
    )


def _fit_text(text: str, font: Font, paint: Paint, max_width: float) -> str:
    if font.measureText(text, paint=paint) <= max_width:
        return text
    ellipsis = "..."
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = text[:middle].rstrip() + ellipsis
        if font.measureText(candidate, paint=paint) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + ellipsis


def _draw_footer_rows(
    canvas: Canvas,
    rows: list[tuple[str, str]],
    x: float,
    first_baseline: float,
    width: float,
    label_width: float,
    label_font: Font,
    value_font: Font,
    label_paint: Paint,
    value_paint: Paint,
    row_height: float,
) -> None:
    for index, (label, value) in enumerate(rows):
        baseline = first_baseline + index * row_height
        canvas.drawString(label, x, baseline, label_font, label_paint)
        value_x = x + label_width
        fitted_value = _fit_text(
            value or "—",
            value_font,
            value_paint,
            width - label_width,
        )
        canvas.drawString(
            fitted_value,
            value_x,
            baseline,
            value_font,
            value_paint,
        )


def _draw_footer(
    ctx: RenderContext,
    canvas: Canvas,
    metadata: RenderMetadata,
    footer_top: int,
    total_width: int,
) -> None:
    config = ctx.config
    footer_bottom = footer_top + config.footer_height
    canvas.drawRect(
        Rect(0, footer_top, total_width, footer_bottom),
        Paint(Color=config.footer_background_color),
    )
    canvas.drawRect(
        Rect(0, footer_top, total_width, footer_top + 2),
        Paint(Color=config.footer_divider_color),
    )

    typeface = _load_typeface(config)
    title_font = Font(typeface, config.footer_title_font_size)
    label_font = Font(typeface, config.footer_label_font_size)
    value_font = Font(typeface, config.footer_value_font_size)
    credit_font = Font(typeface, config.footer_credit_font_size)
    title_paint = Paint(Color=config.footer_title_color, AntiAlias=True)
    label_paint = Paint(Color=config.footer_label_color, AntiAlias=True)
    value_paint = Paint(Color=config.footer_value_color, AntiAlias=True)
    credit_paint = Paint(Color=config.footer_credit_color, AntiAlias=True)

    content_top = footer_top + (config.footer_height - config.footer_jacket_size) / 2
    jacket_left = config.footer_padding
    jacket_rect = Rect(
        jacket_left,
        content_top,
        jacket_left + config.footer_jacket_size,
        content_top + config.footer_jacket_size,
    )
    if metadata.jacket_path and os.path.isfile(metadata.jacket_path):
        jacket = Image.open(metadata.jacket_path)
        crop_size = min(jacket.width(), jacket.height())
        source_left = (jacket.width() - crop_size) / 2
        source_top = (jacket.height() - crop_size) / 2
        canvas.drawImageRect(
            jacket,
            Rect(
                source_left,
                source_top,
                source_left + crop_size,
                source_top + crop_size,
            ),
            jacket_rect,
        )
    else:
        canvas.drawRect(
            jacket_rect,
            Paint(Color=config.footer_jacket_placeholder_color),
        )
        placeholder = "NO JACKET"
        placeholder_width = label_font.measureText(placeholder, paint=label_paint)
        canvas.drawString(
            placeholder,
            jacket_rect.centerX() - placeholder_width / 2,
            jacket_rect.centerY() + config.footer_label_font_size * 0.35,
            label_font,
            label_paint,
        )

    identity_x = (
        jacket_left + config.footer_jacket_size + config.footer_jacket_gap
    )
    title = _fit_text(
        metadata.title or "Untitled",
        title_font,
        title_paint,
        config.footer_identity_width,
    )
    title_baseline = content_top + config.footer_title_font_size
    canvas.drawString(title, identity_x, title_baseline, title_font, title_paint)
    _draw_footer_rows(
        canvas,
        [
            ("Artist", metadata.artist),
            ("Chart Designer", metadata.chart_designer),
            ("Jacket Designer", metadata.jacket_designer),
        ],
        identity_x,
        title_baseline + 55,
        config.footer_identity_width,
        240,
        label_font,
        value_font,
        label_paint,
        value_paint,
        config.footer_row_height,
    )

    judgement_points = get_chart_judgement_points(ctx.chart)
    count_x = (
        identity_x
        + config.footer_identity_width
        + config.footer_section_gap
    )
    _draw_footer_rows(
        canvas,
        [
            ("Combo", str(len(judgement_points))),
            ("Tap", str(len(ctx.get_objects_of_type(Tap)))),
            ("Hold", str(len(ctx.get_objects_of_type(Hold)))),
            ("Flick", str(len(ctx.get_objects_of_type(DirectionalFlick)))),
            ("SkyArea", str(len(ctx.get_objects_of_type(SkyArea)))),
        ],
        count_x,
        content_top + config.footer_value_font_size,
        config.footer_count_width,
        150,
        label_font,
        value_font,
        label_paint,
        value_paint,
        config.footer_row_height,
    )

    detail_x = (
        count_x + config.footer_count_width + config.footer_section_gap
    )
    _draw_footer_rows(
        canvas,
        [
            ("Duration", _format_chart_time(ctx.get_max_object_time())),
            ("BPM", _format_bpm(ctx.chart)),
            ("Level", metadata.level),
        ],
        detail_x,
        content_top + config.footer_value_font_size,
        config.footer_detail_width,
        150,
        label_font,
        value_font,
        label_paint,
        value_paint,
        config.footer_row_height,
    )

    credit = "Generated by YurisakiBot"
    credit_width = credit_font.measureText(credit, paint=credit_paint)
    canvas.drawString(
        credit,
        total_width - config.footer_padding - credit_width,
        footer_bottom - config.footer_padding,
        credit_font,
        credit_paint,
    )


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
    render_beat_lines(ctx, canvas, end_timestamp)
    render_holds(ctx, canvas)
    render_taps(ctx, canvas)
    render_skyareas(ctx, canvas)
    render_directional_flicks(ctx, canvas)
    return surface.makeImageSnapshot()


def _render_pages(
    ctx: RenderContext,
    track_image: Image,
    boundaries: list[int],
    metadata: RenderMetadata,
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
    total_width = max(
        config.page_padding * 2
        + page_count * page_width
        + (page_count - 1) * config.page_gap,
        _footer_min_width(config),
    )
    page_bottom = config.page_padding + page_height
    footer_top = page_bottom + config.footer_track_gap
    total_height = footer_top + config.footer_height

    surface = Surface(total_width, total_height)
    canvas = surface.getCanvas()
    canvas.clear(config.page_background_color)
    _draw_footer(ctx, canvas, metadata, footer_top, total_width)

    typeface = _load_typeface(config)
    font = Font(typeface, config.page_time_font_size)
    time_paint = Paint(Color=config.page_time_color, AntiAlias=True)
    combo_font = Font(typeface, config.page_combo_font_size)
    combo_paint = Paint(Color=config.page_combo_color, AntiAlias=True)
    rhythm_font = Font(typeface, config.page_rhythm_font_size)
    rhythm_paint = Paint(Color=config.page_rhythm_color, AntiAlias=True)
    beat_lines = _beat_line_timestamps_with_bounds(ctx, boundaries[-1])
    judgement_points = get_chart_judgement_points(ctx.chart)
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
            if page_index == 0:
                is_on_page = start_timestamp <= timestamp <= end_timestamp
            else:
                is_on_page = start_timestamp < timestamp <= end_timestamp
            if not is_on_page:
                continue
            y = page_bottom - (ctx.z_offset_for_time(timestamp) - start_z)
            label = _format_chart_time(timestamp)
            label_width = font.measureText(label, paint=time_paint)
            x = track_left - config.page_time_label_gap - label_width
            time_baseline = y + config.page_time_font_size * 0.35
            canvas.drawString(
                label,
                x,
                time_baseline,
                font,
                time_paint,
            )
            combo_label = str(get_combo_before(judgement_points, timestamp))
            combo_width = combo_font.measureText(combo_label, paint=combo_paint)
            combo_x = track_left - config.page_time_label_gap - combo_width
            canvas.drawString(
                combo_label,
                combo_x,
                time_baseline + config.page_combo_font_size + config.page_combo_gap,
                combo_font,
                combo_paint,
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
    chart: Chart,
    jacket_path: str,
    title: str,
    artist: str,
    chart_designer: str = "",
    jacket_designer: str = "",
    level: str = "",
    font_path: str = "",
) -> Image:
    ctx = RenderContext(chart)
    if font_path:
        ctx.config.font_path = font_path
    end_timestamp = ctx.get_max_object_time() + 500
    track_image = _render_track(ctx, end_timestamp)
    boundaries = _page_boundaries(ctx, end_timestamp)
    metadata = RenderMetadata(
        jacket_path=jacket_path,
        title=title,
        artist=artist,
        chart_designer=chart_designer,
        jacket_designer=jacket_designer,
        level=level,
    )
    return _render_pages(ctx, track_image, boundaries, metadata)
