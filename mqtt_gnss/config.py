"""Runtime configuration: broker, topics, iteration count."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    broker_host: str = os.environ.get("MQTT_HOST", "localhost")
    broker_port: int = int(os.environ.get("MQTT_PORT", "1883"))
    keepalive: int = int(os.environ.get("MQTT_KEEPALIVE", "30"))
    client_id_prefix: str = "gnss-bench"

    # Benchmark knobs
    iterations: int = int(os.environ.get("GNSS_ITERATIONS", "300"))
    qos: int = int(os.environ.get("GNSS_QOS", "0"))
    warmup: int = int(os.environ.get("GNSS_WARMUP", "5"))
    response_timeout_s: float = float(os.environ.get("GNSS_TIMEOUT", "5.0"))
    inter_request_delay_s: float = float(os.environ.get("GNSS_DELAY", "0.0"))

    # Topic template. {fmt} is replaced with the format name.
    req_topic_tpl: str = "gnss/{fmt}/req"
    resp_topic_tpl: str = "gnss/{fmt}/resp"

    def req_topic(self, fmt: str) -> str:
        return self.req_topic_tpl.format(fmt=fmt)

    def resp_topic(self, fmt: str) -> str:
        return self.resp_topic_tpl.format(fmt=fmt)


CONFIG = Config()
