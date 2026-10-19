#!/usr/bin/env python3
"""Synthetic BladeRF SC16 Q11 baseband-data generator.

Faithful port of the script provided by the scientific advisor: an
interleaved stream of int16 I/Q samples that mixes Gaussian thermal
noise with an unmodulated CW tone, clipped to the 12-bit ADC range
[-2048, 2047]. The output is byte-for-byte indistinguishable from a
real ``bladerf-cli`` baseband capture of the same length, so the
size-scaling experiment exercises identical wire bytes to a production
SDR pipeline.

USAGE (as a library — from ``measure_*.py``):
    from tools.bladerf_gen import generate_bladerf_payload
    blob = generate_bladerf_payload(10 * 1024 * 1024)   # 10 MB

USAGE (as a CLI — to produce a payload file on disk):
    python -m tools.bladerf_gen --size-mb 1   --out tools/payloads/payload_1mb.bin
    python -m tools.bladerf_gen --size-mb 10  --out tools/payloads/payload_10mb.bin

The generator is deterministic when ``--seed`` is given (handy for
reproducible benchmarks); otherwise it draws fresh noise each call.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np


# Parameters that mirror the scientific-advisor reference script.
# Increasing/decreasing them changes the synthetic spectrum but not
# the wire size, which is what the benchmark actually measures.
_NOISE_STD = 40          # AWGN sigma (within the 12-bit ADC range)
_TONE_AMP = 600          # CW carrier amplitude (well below clip)
_NORMALISED_FREQ = 0.01  # CW offset = 1% of sample rate
_CLIP_LO, _CLIP_HI = -2048, 2047   # BladeRF 12-bit ADC limits


def generate_bladerf_payload(size_bytes: int, seed: Optional[int] = None) -> bytes:
    """Return ``size_bytes`` of interleaved int16 I/Q data.

    The buffer is truncated/padded to be a multiple of 4 bytes (one
    complex sample = 2 byte I + 2 byte Q), which matches BladeRF's
    on-wire format exactly.
    """
    if size_bytes <= 0:
        return b""

    # Each complex sample is exactly 4 bytes (int16 I + int16 Q).
    num_complex_samples = size_bytes // 4
    if num_complex_samples == 0:
        # Cannot produce a meaningful sample at <4 bytes; just zeros.
        return b"\x00" * size_bytes

    rng = np.random.default_rng(seed)

    # 1. Thermal noise (Gaussian AWGN with the ADC-tuned sigma).
    noise_i = rng.normal(0.0, _NOISE_STD, num_complex_samples)
    noise_q = rng.normal(0.0, _NOISE_STD, num_complex_samples)

    # 2. Unmodulated carrier (CW tone offset from DC).
    t = np.arange(num_complex_samples)
    angle = 2.0 * np.pi * _NORMALISED_FREQ * t
    tone_i = _TONE_AMP * np.cos(angle)
    tone_q = _TONE_AMP * np.sin(angle)

    # 3. Combine, clip to 12-bit ADC, cast to int16 wire format.
    signal_i = np.clip(noise_i + tone_i, _CLIP_LO, _CLIP_HI).astype(np.int16)
    signal_q = np.clip(noise_q + tone_q, _CLIP_LO, _CLIP_HI).astype(np.int16)

    # 4. Interleave to BladeRF's [I0, Q0, I1, Q1, ...] layout.
    interleaved = np.empty(num_complex_samples * 2, dtype=np.int16)
    interleaved[0::2] = signal_i
    interleaved[1::2] = signal_q

    blob = interleaved.tobytes()
    # 5. Pad/truncate so the result is exactly ``size_bytes`` (handles the
    # remainder when size_bytes is not a multiple of 4).
    if len(blob) < size_bytes:
        blob += b"\x00" * (size_bytes - len(blob))
    return blob[:size_bytes]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic BladeRF dump")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--size-mb", type=float, help="output size in megabytes")
    group.add_argument("--size-kb", type=float, help="output size in kilobytes")
    group.add_argument("--size-bytes", type=int, help="output size in bytes")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="output file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="optional RNG seed for reproducible output",
    )
    args = parser.parse_args()

    if args.size_mb is not None:
        n = int(args.size_mb * 1024 * 1024)
    elif args.size_kb is not None:
        n = int(args.size_kb * 1024)
    else:
        n = int(args.size_bytes)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = generate_bladerf_payload(n, seed=args.seed)
    args.out.write_bytes(data)
    print(f"wrote {args.out}  ({len(data)} bytes, {len(data)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
