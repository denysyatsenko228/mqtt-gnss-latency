import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm

# ============================================================
# PARAMETERS (same model as delays3.py)
# ============================================================
SEED = 42           # fixes the generated sample, so the plots can be reproduced exactly
N = 100000          # sample size

minL = 5            # constant shift used in the generation
meanL = 1           # lognormal part: mean and sigma of the underlying normal
sigmaL = 1.1

sigmaN = 0.4        # additive normal noise
meanN = 0
magN = 1

HIST_LIMIT = 20     # ms; the histogram only shows values below this (as in delays3.py)
HIST_BINS = 300

# shifts tried for log(x - shift); minL is the one used in the generation
SHIFTS = [4, 4.5, 5, 5.5]

plt.rcParams.update({
    "font.size": 16, "font.weight": "bold",
    "axes.labelweight": "bold", "axes.labelsize": 18, "axes.titleweight": "bold",
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.5,
})

# ============================================================
# SAMPLE (single)
# ============================================================
np.random.seed(SEED)
samples1 = np.random.normal(meanL, sigmaL, N)
samples = np.exp(samples1) + minL + np.random.normal(meanN, sigmaN, N) * magN

print(f"Seed: {SEED}")
print(f"Count: {len(samples)}")
print(f"Min: {np.min(samples):.4f}, Max: {np.max(samples):.4f}")

# ============================================================
# HISTOGRAM
# ============================================================
samples_filtered = samples[samples < HIST_LIMIT]
plt.hist(samples_filtered, HIST_BINS)
plt.xlabel("Round-trip time [ms]")
plt.ylabel("Count")
plt.show()

# ============================================================
# Q-Q PLOTS FOR SEVERAL SHIFTS
# ============================================================
# For each shift, values with x - shift <= 0 have no log and are dropped.
fig, axes = plt.subplots(2, 2, figsize=(14, 11))
for ax, shift in zip(axes.flat, SHIFTS):
    kept = samples[samples > shift]
    logs = np.log(kept - shift)
    print(f"Shift {shift}: kept {len(kept)} of {len(samples)}")
    sm.qqplot(logs, line="s", ax=ax)
    title = f"Shift {shift} ms"
    if shift == minL:
        title += " (used in generation)"
    ax.set_title(title)
    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Sample quantiles")
fig.tight_layout()
plt.show()
