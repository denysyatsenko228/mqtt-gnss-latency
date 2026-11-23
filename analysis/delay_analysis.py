import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.stattools import acf
from statsmodels.graphics.tsaplots import plot_acf

# ============================================================
# PARAMETERS
# ============================================================
FILE = sys.argv[1] if len(sys.argv) > 1 else "generic_10k.csv"
METHOD = sys.argv[2] if len(sys.argv) > 2 else "msgpack"

UPPER_LIMIT = 50        # ms; values at or above it are ignored by the histogram and the log/Q-Q part (None = no limit)
HIST_BINS = 300
MAX_INDEX = 500         # delay-per-iteration plot covers iterations 0..MAX_INDEX-1
MAX_LAG = 10            # autocorrelation lags 0..MAX_LAG
SHIFT = 4.5             # ms; constant subtracted before the log (it may exceed the min; entries <= it are dropped)

plt.rcParams.update({
    "font.size": 16, "font.weight": "bold",
    "axes.labelweight": "bold", "axes.labelsize": 18,
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.5,
})

# ============================================================
# READ
# ============================================================
data = {}
with open(FILE) as measurementsFile:
    reader = csv.reader(measurementsFile)
    next(reader, None)
    for row in reader:
        if not (row[0] in data):
            data[row[0]] = []
        data[row[0]].append(row[2])

if METHOD not in data:
    sys.exit(f"method '{METHOD}' not in {FILE}, available: {list(data)}")

values = np.fromiter(data[METHOD], float)
print(f"File: {FILE}, method: {METHOD}")
print(f"Count: {len(values)}")
print(f"Min: {np.min(values):.4f} ms, Max: {np.max(values):.4f} ms")

values_limited = values if UPPER_LIMIT is None else values[values < UPPER_LIMIT]
print(f"Values below the upper limit ({UPPER_LIMIT}): {len(values_limited)}")

# ============================================================
# HISTOGRAM
# ============================================================
plt.hist(values_limited, HIST_BINS)
plt.xlabel("Round-trip time [ms]")
plt.ylabel("Count")
plt.show()

# ============================================================
# DELAY PER ITERATION
# ============================================================
plt.plot(np.arange(0, MAX_INDEX), values[:MAX_INDEX])
plt.xlabel("Iteration index i")
plt.ylabel("Round-trip time, \u03c4\u1d62 [ms]")
plt.show()

# ============================================================
# AUTOCORRELATION
# ============================================================
acf_values = acf(values, nlags=MAX_LAG)
print("ACF values per lag:")
for lag, value in enumerate(acf_values):
    print(f"  lag {lag}: {value:.4f}")

plot_acf(values, lags=MAX_LAG, title="")
plt.xlabel("Lag k")
plt.ylabel("Autocorrelation")
plt.ylim(-0.25, 1.05)
plt.xticks(range(0, MAX_LAG + 1))
plt.show()

# ============================================================
# CONSTANT SHIFT + LOG + Q-Q
# ============================================================
# Values with x - SHIFT <= 0 have no log and are dropped.
kept = values_limited[values_limited > SHIFT]
logs = np.log(kept - SHIFT)
print(f"Constant: {SHIFT} ms")
print(f"Values kept for log: {len(kept)} of {len(values_limited)} (dropped {len(values_limited) - len(kept)} at or below the constant)")

fig, ax = plt.subplots(figsize=(8, 6))
sm.qqplot(logs, line="s", ax=ax)
ax.set_xlabel("Theoretical quantiles")
ax.set_ylabel("Sample quantiles")
plt.show()
