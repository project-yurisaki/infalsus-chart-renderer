from elements import *
from typing import Optional, get_type_hints
import inspect


_commands = {}


class ParserContext:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.last_skyarea: Optional[SkyArea] = None
        self.max_group_id = 0
        self.bpm = 170.0
        self.bpl = 4.0
        
    def record_group_id(self, group_id: int):
        self.max_group_id = max(self.max_group_id, group_id)
        
    def next_group_id(self) -> int:
        return self.max_group_id + 1


def def_command(name: str):
    def wrapper(func):
        sig = inspect.signature(func) 
        hints = get_type_hints(func) 
        def wrapped(*args, **kwargs): 
            bound = sig.bind(*args, **kwargs) 
            bound.apply_defaults()
            for param_name, value in bound.arguments.items(): 
                if param_name in hints: 
                    expected_type = hints[param_name] 
                    if not isinstance(value, expected_type) and value is not None: 
                        raise TypeError( f"Argument '{param_name}' must be {expected_type}, got {type(value)}" ) 
            return func(*args, **kwargs)
        _commands[name] = wrapped
        return wrapped
    return wrapper


@def_command('chart')
def _chart_info(context: ParserContext, bpm: int | float, bpl: int | float) -> BpmChange:
    context.bpm = bpm
    context.bpl = bpl
    return BpmChange(0, bpm, bpl)


@def_command('bpm')
def _bpm_change(_: ParserContext, timestamp: int, bpm: int | float, bpl: int | float = 4, state: Optional[int] = None) -> BpmChange:
    return BpmChange(timestamp, bpm, bpl)


@def_command('track')
def _track_speed_change(_: ParserContext, timestamp: int, speed: int | float) -> TrackSpeedChange:
    return TrackSpeedChange(timestamp, float(speed))


@def_command('lane')
def _lane_enable_state(_: ParserContext, timestamp: int, lane: int, enable: int):
    return LaneEnableStateChange(timestamp, lane, enable)


@def_command('tap')
def _tap(_: ParserContext, timestamp: int, width: int, lane: int) -> Tap:
    return Tap(timestamp, lane, width)


@def_command('hold')
def _hold(_: ParserContext, timestamp: int, lane: int, width: int, duration: int) -> Hold:
    return Hold(timestamp, lane, width, duration)


@def_command('flick')
def _directional_flick(
    _: ParserContext, timestamp: int,
    x: int, split: int, width: int, direction: int
) -> DirectionalFlick | None:
    if direction not in [0x1, 0x2, 0x4, 0x8]:
        return None
    return DirectionalFlick(timestamp, x / split, width / split, direction)


@def_command('skyarea')
def _sky_area(
    context: ParserContext, timestamp: int, 
    start_x: int, start_x_split: int, start_width: int, 
    end_x: int, end_x_split: int, end_width: int, 
    easing_left: int, easing_right: int,
    duration: int, group_id: Optional[int] = None
) -> SkyArea | None:
    start_x_f = start_x / start_x_split
    start_width_f = start_width / start_x_split
    start_left = start_x_f - start_width_f / 2
    start_right = start_x_f + start_width_f / 2
    end_x_f = end_x / end_x_split
    end_width_f = end_width / end_x_split
    end_left = end_x_f - end_width_f / 2
    end_right = end_x_f + end_width_f / 2
    if start_left < 1e-7 or start_right > (1 + 1e-7) or end_left < 1e-7 or end_right > (1 + 1e-7):
        return None
    easing_types = [0, 1, 2]
    if easing_left not in easing_types or easing_right not in easing_types:
        return None
    if group_id is None:
        if context.last_skyarea is not None and abs(timestamp - context.last_skyarea.timestamp + context.last_skyarea.duration) <= 2:
            group_id = context.last_skyarea.group_id
        else:
            group_id = context.next_group_id()
    context.record_group_id(group_id)
    skyarea = SkyArea(
        timestamp, start_x_f, start_width_f, end_x / end_x_split, end_width / end_x_split,
        easing_left, easing_right, duration, group_id or 0
    )
    context.last_skyarea = skyarea
    return skyarea


def _parse_argument(arg: str) -> int | float:
    arg = arg.strip()
    if '.' in arg:
        return float(arg)
    return int(arg)


def parse_chart(chart: str) -> Chart:
    ctx = ParserContext()
    for line in chart.splitlines():
        if not line:
            continue
        idx = line.index('(')
        cmd = line[:idx].strip()
        if cmd not in _commands:
            raise Exception('Unknown command: {}'.format(cmd))
        args = line[idx+1:line.index(')')].split(',')
        args = [_parse_argument(x) for x in args]
        result = _commands[cmd](ctx, *args)
        if result:
            ctx.events.append(result)
    return Chart(ctx.events, ctx.bpm, ctx.bpl)
