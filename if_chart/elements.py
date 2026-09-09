_counter = 0

class Event:
    def __init__(self, timestamp: int) -> None:
        global _counter
        self.timestamp = timestamp
        self._order = _counter
        _counter += 1
        
    def __lt__(self, another: "Event") -> bool:
        return self.timestamp < another.timestamp or (self.timestamp == another.timestamp and self._order < another._order)
        
    def __str__(self) -> str:
        return type(self).__name__  + '(' + ','.join(['{}={}'.format(k, v) for k, v in self.__dict__.items()]) + ')'
    
    def get_end_timestamp(self) -> int:
        return self.timestamp + getattr(self, 'duration', 0)
    
    __repr__ = __str__


class Tap(Event):
    def __init__(self, timestamp: int, lane: int, width: int) -> None:
        super().__init__(timestamp)
        self.lane = lane
        self.width = width


class Hold(Event):
    def __init__(self, timestamp: int, lane: int, width: int, duration: int) -> None:
        super().__init__(timestamp)
        self.lane = lane
        self.width = width
        self.duration = duration


class SkyArea(Event):
    def __init__(
        self, 
        timestamp: int,
        start_x: float, start_width: float,
        end_x: float, end_width: float,
        easing_left: int, easing_right: int,
        duration: int, group_id: int
    ) -> None:
        super().__init__(timestamp)
        self.start_x = start_x
        self.start_width = start_width
        self.end_x = end_x
        self.end_width = end_width
        self.easing_left = easing_left
        self.easing_right = easing_right
        self.duration = duration
        self.group_id = group_id


class DirectionalFlick(Event):
    def __init__(self, timestamp: int, x: float, width: float, direction: int) -> None:
        super().__init__(timestamp)
        self.x = x
        self.width = width
        self.direction = direction


class BpmChange(Event):
    def __init__(self, timestamp: int, bpm: float, bpl: float) -> None:
        super().__init__(timestamp)
        self.bpm = bpm
        self.bpl = bpl


class TrackSpeedChange(Event):
    def __init__(self, timestamp: int, speed: float) -> None:
        super().__init__(timestamp)
        self.speed = speed


class LaneEnableStateChange(Event):
    def __init__(self, timestamp: int, lane: int, enable: int) -> None:
        super().__init__(timestamp)
        self.lane = lane
        self.enable = enable


class Chart:
    def __init__(self, events: list[Event], bpm: float, bpl: float) -> None:
        self.events = events
        self.bpm = bpm
        self.bpl = bpl
