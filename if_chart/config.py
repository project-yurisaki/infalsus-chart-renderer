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

from pathlib import Path


_ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"


class Config:
    font_path = str(_ASSET_DIRECTORY / "ChironHeiHK-SB.otf")
    pixels_per_sec = int(450 * 0.8)
    # Extreme chart-speed gimmicks can otherwise create tens of thousands of
    # empty pixels in a single millisecond. This only affects preview spacing.
    max_visual_track_speed = 4.0
    track_width = int(600 * 0.8)
    page_target_height = int(4800 * 0.8)
    page_time_column_width = 112
    page_gap = 32
    page_padding = 24
    page_time_font_size = 32
    page_time_label_gap = 12
    page_time_color = 0xFFB9C4D2
    page_combo_font_size = 26
    page_combo_gap = 6
    page_combo_color = 0xFF8E9AAA
    page_rhythm_column_width = 80
    page_rhythm_font_size = 32
    page_rhythm_label_gap = 12
    page_rhythm_color = 0xFFB9C4D2
    page_background_color = 0xFF0B1018
    footer_height = 360
    footer_track_gap = 64
    footer_background_color = 0xFF101722
    footer_divider_color = 0xFF283344
    footer_padding = 36
    footer_jacket_size = 280
    footer_jacket_gap = 32
    footer_identity_width = 620
    footer_count_width = 350
    footer_detail_width = 350
    footer_section_gap = 80
    footer_title_font_size = 44
    footer_label_font_size = 30
    footer_value_font_size = 31
    footer_credit_font_size = 44
    footer_row_height = 44
    footer_title_color = 0xFFF2F5FA
    footer_label_color = 0xFF8390A3
    footer_value_color = 0xFFD6DEE9
    footer_credit_color = 0xFFF2F5FA
    footer_jacket_placeholder_color = 0xFF1B2635
    tap_image_path = str(_ASSET_DIRECTORY / "note.png")
    hold_image_path = str(_ASSET_DIRECTORY / "note_hold.png")
    tap_left_color = 0xFF8B66F0
    tap_right_color = 0xFFE05C88
    hold_color = 0xFF3C92C7
    tap_color = hold_color
    directional_flick_right_color = 0xB05AE0A1
    directional_flick_left_color = 0xB0F6D84A
    directional_flick_height = 64
    directional_flick_tip_inset = 45
    directional_flick_tail_scale = 80
    directional_flick_glow_blur = 4
    directional_flick_edge_width = 2
    # ARGB: the low alpha keeps lane colors and notes visible through the field.
    skyarea_fill_color = 0x50927AE7
    skyarea_edge_glow_color = 0x668A70FF
    skyarea_edge_color = 0xFFF1EAFF
    skyarea_edge_glow_width = 5
    skyarea_edge_glow_blur = 3
    skyarea_edge_width = 2
