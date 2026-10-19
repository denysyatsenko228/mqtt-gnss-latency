#!/usr/bin/env python3
"""Generate raw_mqtt_*.csv files at multiple sample sizes.

Mirrors the project's HTTP-era ``measure.py`` for the MQTT pipeline.
Runs each MQTT serializer through ``GnssPublisher`` and dumps per-sample
round-trip times to CSV with columns ``Method, Time_s, Time_ms`` — the
same layout as the existing ``raw_measurements.csv``.

REQUIREMENTS:
  1. MQTT broker must be running:    mosquitto -p 1883
  2. Subscriber must be running:     python run_server.py
  3. Then run this script in a third terminal.

USAGE:
  python measure_mqtt.py                                       # default 5-format experiment
  python measure_mqtt.py --sizes 1000                          # only one iteration count
  python measure_mqtt.py --sizes 1000 10000                    # subset

  # SIZE-SCALING EXPERIMENT (MsgPack + binary payload)
  python measure_mqtt.py --sizes 1000 --formats msgpack \
      --payload-file tools/payloads/payload_512kb.bin          # use Katin's BladeRF dump
  python measure_mqtt.py --sizes 100 --formats msgpack \
      --payload-size 10485760                                  # synthetic 10 MB payload
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Tuple

from mqtt_gnss import serializers
from mqtt_gnss.client import GnssPublisher
from mqtt_gnss.config import CONFIG
from mqtt_gnss.gnss_data import SAMPLE_RECORD

log = logging.getLogger("measure_mqtt")


def _human_size(n: int) -> str:
    """Compact size suffix for filenames: ``0`` → ``0b``, ``524288`` → ``512kb``."""
    if n == 0:
        return "0b"
    if n % (1024 * 1024) == 0:
        return f"{n // (1024 * 1024)}mb"
    if n % 1024 == 0:
        return f"{n // 1024}kb"
    return f"{n}b"


def _with_payload_suffix(name: str, payload_size: int) -> str:
    """Append ``_pldXXX`` before the file extension when a payload is in use."""
    if payload_size <= 0:
        return name
    p = Path(name)
    return f"{p.stem}_pld{_human_size(payload_size)}{p.suffix}"


def _load_payload(args: argparse.Namespace) -> bytes:
    """Resolve the binary payload from CLI flags. Empty when neither is given."""
    if args.payload_file:
        path = Path(args.payload_file)
        data = path.read_bytes()
        log.info("loaded payload from %s (%d bytes)", path, len(data))
        return data
    if args.payload_size > 0:
        # Lazy import — numpy is only needed when generating a payload, and
        # only by users who actually run the size-scaling experiment.
        from tools.bladerf_gen import generate_bladerf_payload
        data = generate_bladerf_payload(args.payload_size)
        log.info("generated synthetic BladeRF payload (%d bytes)", len(data))
        return data
    return b""


# (sample_count, output_filename) — same per-row layout as raw_measurements.csv
DEFAULT_SIZES: List[Tuple[int, str]] = [
    (1_000,   "raw_mqtt_1k.csv"),
    (10_000,  "raw_mqtt_10k.csv"),
    (100_000, "raw_mqtt_100k.csv"),
]


def run_one(
    n: int,
    output_path: Path,
    formats: Optional[List[str]] = None,
) -> None:
    """Benchmark each requested format for ``n`` iterations and write CSV."""
    # Build an immutable Config override with the desired iteration count.
    cfg = replace(CONFIG, iterations=n)
    pub = GnssPublisher(config=cfg)
    pub.start()
    fmts = formats if formats is not None else serializers.available()

    # (Re)initialise the CSV with header. Old contents (if any) are discarded.
    with output_path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["Method", "Time_s", "Time_ms"])

    try:
        for fmt in fmts:
            log.info("[N=%d] benchmarking %s ...", n, fmt)
            t_start = time.monotonic()
            stats = pub.benchmark_format(fmt)
            wall = time.monotonic() - t_start
            log.info(
                "[N=%d] %s done: collected=%d, mean=%.3f ms, errors=%d, wall=%.1f s",
                n, fmt, stats.count, stats.mean_ms, stats.errors, wall,
            )

            # Append this format's per-sample timings to the CSV.
            with output_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for s in stats.samples_s:
                    writer.writerow([fmt, s, s * 1000.0])
    finally:
        pub.stop()

    log.info("wrote %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT raw-latency CSV generator")
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=None,
        help="iteration counts to benchmark (default: 1000 10000 100000)",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=None,
        help=f"subset of formats to benchmark (default: all available: "
             f"{serializers.available()})",
    )
    parser.add_argument(
        "--payload-size",
        type=int,
        default=0,
        help="bytes of synthetic BladeRF-like payload to inject into every "
             "GnssRecord (default: 0 = no payload). Generated via the "
             "noise+CW algorithm from tools/bladerf_gen.py.",
    )
    parser.add_argument(
        "--payload-file",
        type=str,
        default=None,
        help="path to a binary file used as the payload (e.g. a 512 KB "
             "BladeRF dump produced by tools/csv_to_binary.py). Overrides "
             "--payload-size when given.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Validate ``--formats`` against the loaded registry.
    available_fmts = serializers.available()
    formats = args.formats
    if formats is not None:
        unknown = [f for f in formats if f not in available_fmts]
        if unknown:
            parser.error(f"unknown formats: {unknown}; available: {available_fmts}")

    # Resolve and inject the binary payload (empty by default).
    payload_bytes = _load_payload(args)
    # Global mutation of the canonical sample record. Safe because each
    # script invocation is its own process; the publisher copies the record
    # per iteration with ``dataclasses.replace`` so payload propagates.
    SAMPLE_RECORD.payload = payload_bytes
    payload_size = len(payload_bytes)

    if args.sizes:
        # Reuse the canonical filenames for known sizes; otherwise build one.
        canonical = dict(DEFAULT_SIZES)
        sizes = [(n, canonical.get(n, f"raw_mqtt_{n}.csv")) for n in args.sizes]
    else:
        sizes = DEFAULT_SIZES

    # If a payload is in use, append a size tag to the output filenames so
    # different runs are kept apart automatically.
    sizes = [(n, _with_payload_suffix(name, payload_size)) for n, name in sizes]

    log.info(
        "broker=%s:%d  formats=%s",
        CONFIG.broker_host, CONFIG.broker_port,
        formats if formats is not None else available_fmts,
    )
    log.info("payload: %d bytes (%s)", payload_size, _human_size(payload_size))
    log.info("plan: %s", sizes)

    out_dir = Path(__file__).resolve().parent
    grand_start = time.monotonic()
    for n, filename in sizes:
        path = out_dir / filename
        log.info("==== starting N=%d -> %s ====", n, path)
        t0 = time.monotonic()
        run_one(n, path, formats=formats)
        log.info("==== finished N=%d in %.1f s ====", n, time.monotonic() - t0)
    log.info("ALL DONE in %.1f s", time.monotonic() - grand_start)


if __name__ == "__main__":
    main()
