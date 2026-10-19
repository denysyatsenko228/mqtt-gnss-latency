"""Small compatibility shim across paho-mqtt 1.x and 2.x.

paho-mqtt 2.0 introduced ``CallbackAPIVersion`` and now warns (or errors)
when a ``Client`` is constructed without one. We always request the v1
callback signatures because that's what this project is written against.
"""

from __future__ import annotations

import paho.mqtt.client as mqtt


def make_client(client_id: str, clean_session: bool = True) -> "mqtt.Client":
    CallbackAPIVersion = getattr(mqtt, "CallbackAPIVersion", None)
    if CallbackAPIVersion is not None:
        return mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION1,
            client_id=client_id,
            clean_session=clean_session,
        )
    # paho-mqtt 1.x — no CallbackAPIVersion
    return mqtt.Client(client_id=client_id, clean_session=clean_session)
