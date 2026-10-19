"""MsgPack serializer (binary, schema-less)."""

from __future__ import annotations

import msgpack  # type: ignore[import-not-found]

from ..gnss_data import GnssRecord


class MsgPackSerializer:
    name = "msgpack"

    def encode(self, record: GnssRecord) -> bytes:
        # ``to_dict()`` deliberately omits the ``payload`` bytes field so that
        # text-based serializers stay unaffected. MsgPack handles raw bytes
        # natively (no base64 inflation), so we add the payload back here
        # only if it is non-empty. This keeps small-record encodings as
        # compact as before and lets the "size-scaling" experiment carry
        # multi-megabyte BladeRF SC16 Q11 dumps on the wire without overhead.
        d = record.to_dict()
        if record.payload:
            d["payload"] = record.payload
        return msgpack.packb(d, use_bin_type=True)

    def decode(self, payload: bytes) -> GnssRecord:
        # ``from_dict`` knows about the ``payload`` field, so the bytes are
        # restored automatically when the wire dict contains them.
        return GnssRecord.from_dict(
            msgpack.unpackb(payload, raw=False, strict_map_key=False)
        )
