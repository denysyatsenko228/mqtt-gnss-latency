"""Latency-statistics collector.

Each benchmark run yields a list of round-trip durations (seconds). This
module reduces them into the scalar statistics that the report prints:
mean, min, max, and population standard deviation.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Iterable, List


@dataclass
class LatencyStats:
    format_name: str
    samples_s: List[float] = field(default_factory=list)
    payload_bytes: int = 0      # typical payload size for this format

    # Aggregates (filled by :meth:`finalise`)
    count: int = 0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    std_ms: float = 0.0
    errors: int = 0

    def add_sample(self, seconds: float) -> None:
        self.samples_s.append(seconds)

    def add_error(self) -> None:
        self.errors += 1

    def finalise(self) -> "LatencyStats":
        if not self.samples_s:
            return self
        ms = [s * 1000.0 for s in self.samples_s]
        self.count = len(ms)
        self.mean_ms = statistics.fmean(ms)
        self.min_ms = min(ms)
        self.max_ms = max(ms)
        # Population std deviation — matches numpy's default (ddof=0).
        self.std_ms = math.sqrt(
            sum((x - self.mean_ms) ** 2 for x in ms) / self.count
        )
        return self

    def as_row(self) -> List[str]:
        return [
            self.format_name,
            str(self.count),
            f"{self.payload_bytes}",
            f"{self.mean_ms:8.3f}",
            f"{self.min_ms:8.3f}",
            f"{self.max_ms:8.3f}",
            f"{self.std_ms:8.3f}",
            str(self.errors),
        ]


HEADER = ["format", "N", "bytes", "mean,ms", "min,ms", "max,ms", "std,ms", "err"]


def format_report(rows: Iterable[LatencyStats]) -> str:
    """Render a fixed-width ASCII table comparing the formats."""
    rows = [r.finalise() for r in rows]
    lines = [" | ".join(f"{h:>8}" for h in HEADER)]
    lines.append("-+-".join("-" * 8 for _ in HEADER))
    for r in rows:
        lines.append(" | ".join(f"{c:>8}" for c in r.as_row()))
    return "\n".join(lines)
