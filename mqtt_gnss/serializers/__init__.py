"""Pluggable serializers and a small registry for the benchmark runner.

Every serializer exposes the :class:`Serializer` protocol: ``encode`` takes a
:class:`mqtt_gnss.gnss_data.GnssRecord` and returns ``bytes``; ``decode``
does the inverse. The registry is populated lazily so that optional
dependencies (protobuf, msgpack, toon_format) don't break import-time.
"""

from __future__ import annotations

from typing import Dict, List

from .base import Serializer
from .json_ser import JsonSerializer
from .nmea_ser import NmeaSerializer

_REGISTRY: Dict[str, Serializer] = {
    "json": JsonSerializer(),
    "nmea": NmeaSerializer(),
}

# Optional serializers — registered only when their deps are importable.
try:
    from .protobuf_ser import ProtobufSerializer  # noqa: WPS433
    _REGISTRY["protobuf"] = ProtobufSerializer()
except Exception as exc:  # pragma: no cover — depends on install state
    import warnings
    warnings.warn(f"protobuf serializer disabled: {exc}")

try:
    from .msgpack_ser import MsgPackSerializer  # noqa: WPS433
    _REGISTRY["msgpack"] = MsgPackSerializer()
except Exception as exc:  # pragma: no cover
    import warnings
    warnings.warn(f"msgpack serializer disabled: {exc}")

try:
    from .toon_ser import ToonSerializer  # noqa: WPS433
    _REGISTRY["toon"] = ToonSerializer()
except Exception as exc:  # pragma: no cover
    import warnings
    warnings.warn(f"toon serializer disabled: {exc}")


def available() -> List[str]:
    """Names of serializers that loaded successfully."""
    return list(_REGISTRY.keys())


def get(name: str) -> Serializer:
    try:
        return _REGISTRY[name]
    except KeyError as exc:  # pragma: no cover
        raise KeyError(
            f"unknown format {name!r}; available: {sorted(_REGISTRY)}"
        ) from exc


__all__ = ["Serializer", "available", "get"]
