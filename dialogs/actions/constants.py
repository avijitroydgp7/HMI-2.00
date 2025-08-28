from enum import Enum


class ActionType(str, Enum):
    BIT = "bit"
    WORD = "word"

    @classmethod
    def values(cls):
        return [m.value for m in cls]


class TriggerMode(str, Enum):
    ORDINARY = "Ordinary"
    ON = "On"
    OFF = "Off"
    RANGE = "Range"

    @classmethod
    def values(cls):
        return [m.value for m in cls]

