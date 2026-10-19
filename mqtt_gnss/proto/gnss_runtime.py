"""Runtime-built protobuf message, used when ``gnss_pb2`` isn't available.

Building the descriptor programmatically means the benchmark runs even
without invoking ``protoc`` — you still get a real protobuf wire format
for latency comparisons. The schema must stay in sync with
``gnss.proto``.
"""

from __future__ import annotations

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

_FDP = descriptor_pb2.FieldDescriptorProto

_file_proto = descriptor_pb2.FileDescriptorProto(
    name="mqtt_gnss/proto/gnss_runtime.proto",
    syntax="proto3",
    package="mqtt_gnss_runtime",
)
_msg = _file_proto.message_type.add(name="GnssRecord")


def _add(name: str, number: int, typ: int) -> None:
    f = _msg.field.add()
    f.name = name
    f.number = number
    f.type = typ
    f.label = _FDP.LABEL_OPTIONAL


_add("seq", 1, _FDP.TYPE_UINT64)
_add("sent_ns", 2, _FDP.TYPE_UINT64)
_add("time_utc", 3, _FDP.TYPE_STRING)
_add("status", 4, _FDP.TYPE_STRING)
_add("latitude", 5, _FDP.TYPE_DOUBLE)
_add("lat_hemi", 6, _FDP.TYPE_STRING)
_add("longitude", 7, _FDP.TYPE_DOUBLE)
_add("lon_hemi", 8, _FDP.TYPE_STRING)
_add("speed_knots", 9, _FDP.TYPE_DOUBLE)
_add("course_deg", 10, _FDP.TYPE_DOUBLE)
_add("date", 11, _FDP.TYPE_STRING)
_add("mag_var", 12, _FDP.TYPE_DOUBLE)
_add("mag_var_dir", 13, _FDP.TYPE_STRING)
_add("mode", 14, _FDP.TYPE_STRING)
_add("checksum", 15, _FDP.TYPE_STRING)

# Use a fresh pool so repeat imports (module reloads, tests) don't hit
# "file already exists" errors on the default pool.
_pool = descriptor_pool.DescriptorPool()
_file_desc = _pool.Add(_file_proto)

_msg_desc = _file_desc.message_types_by_name["GnssRecord"]

# protobuf >= 4.24 exposes GetMessageClass; older releases used MessageFactory.
if hasattr(message_factory, "GetMessageClass"):
    GnssRecord = message_factory.GetMessageClass(_msg_desc)
else:  # pragma: no cover — legacy fallback
    GnssRecord = message_factory.MessageFactory(_pool).GetPrototype(_msg_desc)  # type: ignore[attr-defined]

__all__ = ["GnssRecord"]
