"""Raw NMEA 0183 ``$GPRMC`` serializer.

The measurement metadata (``seq``, ``sent_ns``) cannot be expressed in a
real RMC sentence, so we prepend a tiny header ``<seq>,<sent_ns>|`` ahead
of the ``$GPRMC,…*XX`` payload. This keeps the on-the-wire bytes close to
what a real receiver would emit while still letting the benchmark pair
requests with responses.
"""

from __future__ import annotations

from ..gnss_data import GnssRecord


def _nmea_checksum(body: str) -> str:
    """XOR of every char between ``$`` and ``*`` as two upper-case hex digits."""
    c = 0
    for ch in body:
        c ^= ord(ch)
    return f"{c:02X}"


def _deg_to_nmea(value: float, is_lat: bool) -> str:
    """Decimal degrees → ``DDMM.MMMM`` / ``DDDMM.MMMM`` NMEA field."""
    deg_width = 2 if is_lat else 3
    v = abs(value)
    d = int(v)
    m = (v - d) * 60.0
    return f"{d:0{deg_width}d}{m:07.4f}"


def _nmea_to_deg(field: str) -> float:
    if not field:
        return 0.0
    # RMC uses ddmm.mmmm (lat) or dddmm.mmmm (lon); split on the '.'.
    dot = field.index(".")
    deg = int(field[: dot - 2])
    mins = float(field[dot - 2:])
    return deg + mins / 60.0


class NmeaSerializer:
    name = "nmea"

    def encode(self, record: GnssRecord) -> bytes:
        body = (
            f"GPRMC,{record.time_utc},{record.status},"
            f"{_deg_to_nmea(record.latitude, True)},{record.lat_hemi},"
            f"{_deg_to_nmea(record.longitude, False)},{record.lon_hemi},"
            f"{record.speed_knots:.2f},{record.course_deg:.2f},"
            f"{record.date},,{record.mode}"
        )
        sentence = f"${body}*{_nmea_checksum(body)}"
        header = f"{record.seq},{record.sent_ns}|"
        return (header + sentence).encode("ascii")

    def decode(self, payload: bytes) -> GnssRecord:
        text = payload.decode("ascii")
        header, sentence = text.split("|", 1)
        seq_s, sent_ns_s = header.split(",", 1)

        body, _checksum = sentence[1:].split("*", 1)  # drop leading '$'
        parts = body.split(",")
        # Expected layout: GPRMC, time, status, lat, N/S, lon, E/W, speed,
        #                  course, date, magvar, magvar-dir (we pack mode here)
        return GnssRecord(
            seq=int(seq_s),
            sent_ns=int(sent_ns_s),
            time_utc=parts[1],
            status=parts[2],
            latitude=_nmea_to_deg(parts[3]),
            lat_hemi=parts[4] or "N",
            longitude=_nmea_to_deg(parts[5]),
            lon_hemi=parts[6] or "E",
            speed_knots=float(parts[7]) if parts[7] else 0.0,
            course_deg=float(parts[8]) if parts[8] else 0.0,
            date=parts[9],
            mode=parts[11] if len(parts) > 11 else "A",
        )
