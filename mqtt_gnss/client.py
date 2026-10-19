"""MQTT publisher — the benchmark driver.

For each enabled format it performs ``config.iterations`` round trips
(publish on ``gnss/<format>/req``, wait for ``gnss/<format>/resp``),
collects the RTT samples into a :class:`LatencyStats`, and finally prints
a comparison table.
"""

from __future__ import annotations

import argparse
import logging
import threading
import time
from dataclasses import replace
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt

from . import serializers
from ._mqtt_compat import make_client
from .config import CONFIG, Config
from .gnss_data import SAMPLE_RECORD, GnssRecord
from .measurement import LatencyStats, format_report
from .plotting import plot_latency

log = logging.getLogger("mqtt_gnss.client")


class _PendingMap:
    """Thread-safe ``seq -> Event`` registry for matching responses to requests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: Dict[int, threading.Event] = {}
        self._responses: Dict[int, bytes] = {}

    def register(self, seq: int) -> threading.Event:
        ev = threading.Event()
        with self._lock:
            self._events[seq] = ev
        return ev

    def complete(self, seq: int, payload: bytes) -> None:
        with self._lock:
            ev = self._events.pop(seq, None)
            if ev is None:
                return
            self._responses[seq] = payload
        ev.set()

    def pop_response(self, seq: int) -> Optional[bytes]:
        with self._lock:
            return self._responses.pop(seq, None)


class GnssPublisher:
    def __init__(self, config: Config = CONFIG) -> None:
        self.config = config
        self.client_id = f"{config.client_id_prefix}-pub"
        self._client = make_client(self.client_id, clean_session=True)
        self._pending = _PendingMap()
        self._current_fmt: Optional[str] = None
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._connected = threading.Event()

    # ---- paho callbacks ------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):  # noqa: N802
        if rc != 0:
            log.error("broker connect failed: rc=%s", rc)
            return
        self._connected.set()

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):  # noqa: N802
        fmt = self._current_fmt
        if fmt is None or msg.topic != self.config.resp_topic(fmt):
            return
        ser = serializers.get(fmt)
        try:
            record = ser.decode(msg.payload)
        except Exception as exc:
            log.warning("drop malformed %s response: %s", fmt, exc)
            return
        self._pending.complete(record.seq, msg.payload)

    # ---- lifecycle -----------------------------------------------------
    def start(self) -> None:
        self._client.connect(
            self.config.broker_host,
            self.config.broker_port,
            keepalive=self.config.keepalive,
        )
        self._client.loop_start()
        if not self._connected.wait(self.config.response_timeout_s):
            raise RuntimeError("failed to connect to MQTT broker")

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    # ---- benchmark -----------------------------------------------------
    def benchmark_format(self, fmt: str) -> LatencyStats:
        ser = serializers.get(fmt)
        stats = LatencyStats(format_name=fmt)

        # Swap the subscription to the format currently under test.
        if self._current_fmt is not None:
            self._client.unsubscribe(self.config.resp_topic(self._current_fmt))
        self._current_fmt = fmt
        self._client.subscribe(self.config.resp_topic(fmt), qos=self.config.qos)

        # Brief pause to let the subscribe land before the first publish.
        time.sleep(0.05)

        req_topic = self.config.req_topic(fmt)
        total = self.config.iterations + self.config.warmup
        for i in range(total):
            record = replace(SAMPLE_RECORD, seq=i, sent_ns=time.monotonic_ns())
            payload = ser.encode(record)
            ev = self._pending.register(i)
            t0 = time.monotonic()
            self._client.publish(req_topic, payload, qos=self.config.qos)
            if not ev.wait(self.config.response_timeout_s):
                stats.add_error()
                log.warning("%s seq=%d timed out", fmt, i)
                continue
            elapsed = time.monotonic() - t0
            self._pending.pop_response(i)

            # Discard warmup samples and record the typical payload size
            # once (all encoded samples have the same shape).
            if i >= self.config.warmup:
                stats.add_sample(elapsed)
                if stats.payload_bytes == 0:
                    stats.payload_bytes = len(payload)

            if self.config.inter_request_delay_s:
                time.sleep(self.config.inter_request_delay_s)

        return stats.finalise()


def main() -> None:
    parser = argparse.ArgumentParser(description="GNSS MQTT latency benchmark (publisher)")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=None,
        help=f"subset of: {serializers.available()} (default: all)",
    )
    parser.add_argument(
        "--chart",
        default="latency_chart.png",
        help="output path for the bar chart (empty string disables the chart)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    formats: List[str] = args.formats or serializers.available()
    unknown = [f for f in formats if f not in serializers.available()]
    if unknown:
        parser.error(f"unknown formats: {unknown}; available: {serializers.available()}")

    pub = GnssPublisher()
    pub.start()
    try:
        results: List[LatencyStats] = []
        for fmt in formats:
            log.info("benchmarking %s …", fmt)
            results.append(pub.benchmark_format(fmt))
        print()
        print(format_report(results))

        if args.chart:
            path = plot_latency(results, args.chart, iterations=pub.config.iterations)
            if path:
                print()
                print(f"Chart written to: {path}")
    finally:
        pub.stop()


if __name__ == "__main__":
    main()
