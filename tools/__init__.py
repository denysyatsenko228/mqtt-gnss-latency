"""Helper utilities for the size-scaling experiment.

These tools generate the binary payloads used by ``measure_mqtt.py`` /
``measure_https.py`` when running with ``--payload-size`` or
``--payload-file``. They are intentionally separate from the core
``mqtt_gnss`` / ``https_gnss`` packages so the benchmark code remains
unaware of how payloads are produced.
"""
