#!/usr/bin/env python3
"""Convert a BladeRF I/Q CSV (the form Katin provided) into the binary
SC16 Q11 wire format that a real ``bladerf-cli`` capture would produce.

The CSV is just a human-readable representation: three columns,
``sample_index, real, imag``, with ``real`` and ``imag`` already
normalised into roughly [-1, +1] (i.e. divided by the 12-bit ADC's
positive range). The binary form is what a real receiver pushes onto
the bus and what we therefore want to transmit through MQTT/HTTPS.

Conversion: float * 2048 → int16, interleaved [I0, Q0, I1, Q1, ...].
A 131 072-sample CSV produces exactly 524 288 bytes = 512 KB binary —
the reference size used by the size-scaling experiment.

USAGE:
    python -m tools.csv_to_binary \
        --in  uploads/record_0_az_0j.csv \
        --out tools/payloads/payload_512kb.bin
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


# 12-bit ADC scale: a normalised value of 1.0 corresponds to the max
# positive ADC reading of +2047 (or -2048 on the negative side).
_ADC_SCALE = 2048
_CLIP_LO, _CLIP_HI = -2048, 2047


def convert(in_path: Path, out_path: Path) -> int:
    """Read CSV → write SC16 Q11 binary. Returns the byte count written."""
    reals: list[float] = []
    imags: list[float] = []
    with in_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reals.append(float(row["real"]))
            imags.append(float(row["imag"]))

    if not reals:
        raise ValueError(f"empty CSV: {in_path}")

    # ``np.round`` is the difference between matching the original int16
    # values bit-for-bit vs. losing the lowest bit through int16's default
    # truncation-toward-zero. The CSV is just a lossy float view of the
    # already-quantised ADC output; rounding recovers the underlying value.
    i_scaled = np.round(np.array(reals) * _ADC_SCALE)
    q_scaled = np.round(np.array(imags) * _ADC_SCALE)
    i_arr = np.clip(i_scaled, _CLIP_LO, _CLIP_HI).astype(np.int16)
    q_arr = np.clip(q_scaled, _CLIP_LO, _CLIP_HI).astype(np.int16)

    # Interleave [I0, Q0, I1, Q1, ...] — BladeRF's native layout.
    interleaved = np.empty(len(i_arr) * 2, dtype=np.int16)
    interleaved[0::2] = i_arr
    interleaved[1::2] = q_arr

    out_path.parent.mkdir(parents=True, exist_ok=True)
    blob = interleaved.tobytes()
    out_path.write_bytes(blob)
    return len(blob)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert BladeRF I/Q CSV to SC16 Q11 binary"
    )
    parser.add_argument("--in", dest="in_path", type=Path, required=True)
    parser.add_argument("--out", dest="out_path", type=Path, required=True)
    args = parser.parse_args()

    n = convert(args.in_path, args.out_path)
    print(
        f"wrote {args.out_path}  ({n} bytes, {n / 1024:.1f} KB, "
        f"{n // 4} complex samples)"
    )


if __name__ == "__main__":
    main()
