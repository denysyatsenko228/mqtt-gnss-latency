"""Serializer protocol."""

from __future__ import annotations

from typing import Protocol

from ..gnss_data import GnssRecord


class Serializer(Protocol):
    name: str

    def encode(self, record: GnssRecord) -> bytes: ...
    def decode(self, payload: bytes) -> GnssRecord: ...
