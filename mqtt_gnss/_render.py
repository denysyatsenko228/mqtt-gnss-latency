"""Display labels used on the latency bar chart."""

from __future__ import annotations

_LABELS = {
    "json": "JSON",
    "nmea": "Raw NMEA",
    "protobuf": "Protobuf",
    "msgpack": "MsgPack",
    "toon": "TOON",
}


def format_label(fmt: str) -> str:
    return _LABELS.get(fmt, fmt.upper())
