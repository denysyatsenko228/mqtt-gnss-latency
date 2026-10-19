"""Matplotlib chart that mirrors the original project's latency plot."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence, Union

from ._render import format_label
from .measurement import LatencyStats

log = logging.getLogger(__name__)


def plot_latency(
    stats: Sequence[LatencyStats],
    path: Union[str, Path] = "latency_chart.png",
    iterations: Optional[int] = None,
) -> Optional[str]:
    """Save a bar chart of mean round-trip latency per format.

    Returns the output path on success, ``None`` if matplotlib isn't
    installed or no samples are available.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless-safe backend
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover — optional dep
        log.warning("matplotlib not available, skipping chart: %s", exc)
        return None

    ordered = [s for s in stats if s.count > 0]
    if not ordered:
        log.warning("no samples to plot")
        return None

    ordered = sorted(ordered, key=lambda s: s.mean_ms)
    labels = [format_label(s.format_name) for s in ordered]
    means = [s.mean_ms for s in ordered]

    if iterations is None:
        iterations = max(s.count for s in ordered)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    bars = ax.bar(labels, means, color="#1f77b4")
    ax.set_title(
        f"Порівняння середньої затримки передачі GNSS/NMEA повідомлень (n={iterations})"
    )
    ax.set_xlabel("Спосіб передачі")
    ax.set_ylabel("Середня затримка, мс")
    ax.set_ylim(0, max(means) * 1.15 if means else 1.0)

    for b, m in zip(bars, means):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height(),
            f"{m:.3f}",
            ha="center",
            va="bottom",
        )

    fig.tight_layout()
    out = Path(path)
    fig.savefig(out)
    plt.close(fig)
    log.info("wrote latency chart to %s", out)
    return str(out)
