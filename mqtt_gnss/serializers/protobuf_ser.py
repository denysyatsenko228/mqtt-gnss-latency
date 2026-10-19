"""Protobuf serializer.

Load order — the first path that succeeds wins:

1. ``mqtt_gnss.proto.gnss_pb2`` — the code ``protoc`` produces from
   ``gnss.proto``. This is preferred in production.
2. On-the-fly compile via ``grpc_tools.protoc`` if it's installed.
3. ``mqtt_gnss.proto.gnss_runtime`` — a descriptor built at import time
   using ``google.protobuf``'s runtime reflection. Needs no codegen and
   no ``protoc`` binary, so the benchmark is usable out of the box.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from ..gnss_data import GnssRecord

log = logging.getLogger(__name__)


def _compile_with_grpc_tools() -> Any:  # pragma: no cover — dev-only
    from grpc_tools import protoc  # type: ignore[import-not-found]

    proto_dir = Path(__file__).resolve().parent.parent / "proto"
    proto_file = proto_dir / "gnss.proto"
    rc = protoc.main([
        "protoc",
        f"-I{proto_dir}",
        f"--python_out={proto_dir}",
        str(proto_file),
    ])
    if rc != 0:
        raise RuntimeError(f"protoc exited with status {rc}")
    return importlib.import_module("mqtt_gnss.proto.gnss_pb2")


def _load_proto_module() -> Any:
    try:
        return importlib.import_module("mqtt_gnss.proto.gnss_pb2")
    except ModuleNotFoundError:
        pass
    try:
        return _compile_with_grpc_tools()
    except Exception as exc:
        log.info("grpc_tools protoc unavailable (%s); using runtime descriptor", exc)
    return importlib.import_module("mqtt_gnss.proto.gnss_runtime")


_proto = _load_proto_module()


class ProtobufSerializer:
    name = "protobuf"

    def encode(self, record: GnssRecord) -> bytes:
        m = _proto.GnssRecord(
            seq=record.seq,
            sent_ns=record.sent_ns,
            time_utc=record.time_utc,
            status=record.status,
            latitude=record.latitude,
            lat_hemi=record.lat_hemi,
            longitude=record.longitude,
            lon_hemi=record.lon_hemi,
            speed_knots=record.speed_knots,
            course_deg=record.course_deg,
            date=record.date,
            mag_var=record.mag_var,
            mag_var_dir=record.mag_var_dir,
            mode=record.mode,
            checksum=record.checksum,
        )
        return m.SerializeToString()

    def decode(self, payload: bytes) -> GnssRecord:
        m = _proto.GnssRecord()
        m.ParseFromString(payload)
        return GnssRecord(
            seq=m.seq,
            sent_ns=m.sent_ns,
            time_utc=m.time_utc,
            status=m.status,
            latitude=m.latitude,
            lat_hemi=m.lat_hemi,
            longitude=m.longitude,
            lon_hemi=m.lon_hemi,
            speed_knots=m.speed_knots,
            course_deg=m.course_deg,
            date=m.date,
            mag_var=m.mag_var,
            mag_var_dir=m.mag_var_dir,
            mode=m.mode,
            checksum=m.checksum,
        )
