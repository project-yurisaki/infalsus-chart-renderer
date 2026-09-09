from bisect import bisect_left

from .elements import (
    BpmChange,
    Chart,
    DirectionalFlick,
    Hold,
    SkyArea,
    Tap,
)


def get_judgement_points(start_time: int, end_time: int, bpm: float, leading_judgement_point: bool) -> list[float]:
    # hold has leading judgement point while skyarea not
    # input/output unit: ms
    duration = end_time - start_time
    result: list[float] = []

    if bpm >= 249.99:
        interval = 60000.0 / (bpm * 0.5) / 2.0
    else:
        interval = 60000.0 / bpm / 2.0

    if leading_judgement_point:
        result.append(start_time)

    offset = 0.0
    while offset + interval <= duration:
        offset += interval
        result.append(start_time + offset)

    if duration - offset >= 2.0:
        result.append(end_time)

    return result


def _get_bpm_at(chart: Chart, timestamp: int) -> float:
    bpm = chart.bpm
    for change in sorted(
        (event for event in chart.events if isinstance(event, BpmChange)),
        key=lambda event: event.timestamp,
    ):
        if change.timestamp > timestamp:
            break
        bpm = change.bpm
    return bpm


def get_chart_judgement_points(chart: Chart) -> list[float]:
    result = []
    for event in chart.events:
        if isinstance(event, (Tap, DirectionalFlick)):
            result.append(event.timestamp)
            continue
        if not isinstance(event, (Hold, SkyArea)):
            continue

        bpm = _get_bpm_at(chart, event.timestamp)
        if bpm <= 0:
            continue
        result.extend(
            get_judgement_points(
                event.timestamp,
                event.get_end_timestamp(),
                bpm,
                leading_judgement_point=isinstance(event, Hold),
            )
        )
    result.sort()
    return result


def get_combo_before(judgement_points: list[float], timestamp: int) -> int:
    return bisect_left(judgement_points, timestamp)
