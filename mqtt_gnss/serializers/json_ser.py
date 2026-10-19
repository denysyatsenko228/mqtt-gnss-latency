"""JSON serializer — the baseline."""

from __future__ import annotations

import json

from ..gnss_data import GnssRecord


class JsonSerializer:
    name = "json"

    def encode(self, record: GnssRecord) -> bytes:
        return json.dumps(record.to_dict(), separators=(",", ":")).encode("utf-8")

    def decode(self, payload: bytes) -> GnssRecord:
        return GnssRecord.from_dict(json.loads(payload.decode("utf-8")))
