"""Canonical in-memory representation of a GNSS (GPS RMC) record.

All serializers translate to/from :class:`GnssRecord`, which carries the
numeric fields we care about plus a monotonically-increasing sequence id
used to correlate publish/response messages in the benchmark.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass
class GnssRecord:
    # Correlation / measurement metadata
    seq: int = 0
    sent_ns: int = 0          # publisher-side monotonic timestamp (ns)

    # GNSS payload (fields mirror a typical $GPRMC sentence)
    # Fields mirror the example in ``gps_log.txt``: ``5025.9183 N`` means
    # 50°25.9183' in NMEA's DDMM.MMMM form. We store decimal degrees
    # (≈ 50.4320) and let the NMEA serializer reconstruct the original.
    time_utc: str = "044027.000"
    status: str = "A"
    latitude: float = 50.0 + 25.9183 / 60.0   # decimal degrees (≈ 50.43197)
    lat_hemi: str = "N"
    longitude: float = 30.0 + 27.7837 / 60.0  # decimal degrees (≈ 30.46306)
    lon_hemi: str = "E"
    speed_knots: float = 0.30
    course_deg: float = 196.20
    date: str = "190226"          # ddmmyy
    mag_var: float = 0.0
    mag_var_dir: str = "E"
    mode: str = "A"
    checksum: str = "02"

    # Optional binary payload used by the "size-scaling" experiment to
    # simulate real BladeRF SC16 Q11 dumps. It is **excluded** from
    # :meth:`to_dict` so the text-based serializers (JSON, NMEA, TOON) are
    # not affected by its presence. Only MsgPack injects it on the wire,
    # taking advantage of MsgPack's native ``bytes`` type — no base64
    # inflation, faithful to how a real receiver would push raw samples.
    payload: bytes = b""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Strip bytes from the generic dict view so dict-based serializers
        # (json/toon) and the dataclass-introspection in toon_ser keep
        # working unchanged.
        d.pop("payload", None)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GnssRecord":
        # Accept partial dicts (unknown keys ignored, missing keys defaulted).
        # ``payload`` *is* a known field, so when MsgPack puts it back into
        # the dict on decode it is restored automatically here.
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


#: Example record — mirrors the ``gps_log.txt`` that ships with the project.
SAMPLE_RECORD = GnssRecord()
