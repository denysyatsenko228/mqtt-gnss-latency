"""TOON serializer (experimental).

Uses ``toon_format`` when available. Falls back to a minimal key=value
text encoder so the benchmark keeps running without the optional dep.

The fallback restores field types from :class:`GnssRecord`'s dataclass
annotations, which matters for GNSS values like ``"044027.000"`` that
*look* numeric but must remain strings.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict

from ..gnss_data import GnssRecord

try:
    import toon_format  # type: ignore[import-not-found]
    _HAVE_TOON = True
except Exception:  # pragma: no cover
    toon_format = None  # type: ignore[assignment]
    _HAVE_TOON = False


_FIELD_TYPES: Dict[str, type] = {
    f.name: f.type if isinstance(f.type, type) else str  # dataclass may give str annotations
    for f in dataclasses.fields(GnssRecord)
}
# dataclass field types can come back as forward-ref strings (when
# ``from __future__ import annotations`` is in effect). Rebuild the map
# using the resolved class attributes from a default instance instead.
_FIELD_TYPES = {k: type(v) for k, v in GnssRecord().to_dict().items()}


def _coerce(d: Dict[str, Any]) -> Dict[str, Any]:
    """Cast textual values back to their declared dataclass types."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        target = _FIELD_TYPES.get(k)
        if target is None or isinstance(v, target):
            out[k] = v
            continue
        if target is int:
            try:
                out[k] = int(v)
                continue
            except (TypeError, ValueError):
                pass
        if target is float:
            try:
                out[k] = float(v)
                continue
            except (TypeError, ValueError):
                pass
        # Default: leave as-is (string fields stay strings).
        out[k] = v
    return out


def _fallback_encode(d: Dict[str, Any]) -> bytes:
    return ("\n".join(f"{k}={v}" for k, v in d.items())).encode("utf-8")


def _fallback_decode(payload: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for line in payload.decode("utf-8").splitlines():
        if not line:
            continue
        k, _, v = line.partition("=")
        out[k] = v
    return out


class ToonSerializer:
    name = "toon"

    def encode(self, record: GnssRecord) -> bytes:
        d = record.to_dict()
        if _HAVE_TOON:
            try:
                return toon_format.dumps(d).encode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                pass
        return _fallback_encode(d)

    def decode(self, payload: bytes) -> GnssRecord:
        if _HAVE_TOON:
            try:
                return GnssRecord.from_dict(
                    _coerce(toon_format.loads(payload.decode("utf-8")))  # type: ignore[attr-defined]
                )
            except Exception:
                pass
        return GnssRecord.from_dict(_coerce(_fallback_decode(payload)))
