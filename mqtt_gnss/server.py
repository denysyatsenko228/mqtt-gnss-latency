"""MQTT subscriber — the "server" side of the benchmark.

It listens on ``gnss/<format>/req`` for every registered format, deserialises
the payload to validate round-trip correctness, then republishes on
``gnss/<format>/resp`` with the same ``seq``/``sent_ns`` so the publisher
can compute round-trip time.
"""

from __future__ import annotations

import logging
import signal
import threading
from typing import Dict

import paho.mqtt.client as mqtt

from . import serializers
from ._mqtt_compat import make_client
from .config import CONFIG, Config
from .gnss_data import GnssRecord

log = logging.getLogger("mqtt_gnss.server")


class GnssSubscriber:
    def __init__(self, config: Config = CONFIG) -> None:
        self.config = config
        self._client = make_client(f"{config.client_id_prefix}-sub", clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._stop = threading.Event()
        self._serializers: Dict[str, serializers.Serializer] = {
            name: serializers.get(name) for name in serializers.available()
        }

    # ---- paho callbacks ------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):  # noqa: D401,N802
        if rc != 0:
            log.error("broker connect failed: rc=%s", rc)
            return
        for name in self._serializers:
            topic = self.config.req_topic(name)
            client.subscribe(topic, qos=self.config.qos)
            log.info("subscribed: %s (qos=%d)", topic, self.config.qos)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):  # noqa: N802
        # Topic layout: gnss/<format>/req
        try:
            _, fmt, suffix = msg.topic.split("/")
        except ValueError:
            log.warning("ignoring unknown topic: %s", msg.topic)
            return
        if suffix != "req":
            return

        ser = self._serializers.get(fmt)
        if ser is None:
            log.warning("no serializer for %r", fmt)
            return

        try:
            record: GnssRecord = ser.decode(msg.payload)
        except Exception as exc:
            log.error("decode failed on %s: %s", msg.topic, exc)
            return

        # Echo the same record back (re-encoded) on the response topic.
        try:
            out = ser.encode(record)
        except Exception as exc:
            log.error("encode failed on %s: %s", msg.topic, exc)
            return
        client.publish(self.config.resp_topic(fmt), out, qos=self.config.qos)

    # ---- lifecycle -----------------------------------------------------
    def serve_forever(self) -> None:
        self._client.connect(
            self.config.broker_host,
            self.config.broker_port,
            keepalive=self.config.keepalive,
        )
        log.info(
            "GNSS MQTT subscriber connected to %s:%d; formats=%s",
            self.config.broker_host,
            self.config.broker_port,
            list(self._serializers),
        )
        self._client.loop_start()
        try:
            self._stop.wait()
        finally:
            self._client.loop_stop()
            self._client.disconnect()

    def stop(self, *_: object) -> None:
        self._stop.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    sub = GnssSubscriber()
    signal.signal(signal.SIGINT, sub.stop)
    signal.signal(signal.SIGTERM, sub.stop)
    sub.serve_forever()


if __name__ == "__main__":
    main()
