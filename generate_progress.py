"""Generate a Karpathy-style progress.png for the autoresearch run."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# Data from results.tsv
experiments = [
    ("Baseline", 74.72, "keep"),
    ("Exp 1:\nCore rules +\n2 examples", 88.06, "keep"),
    ("Exp 2:\nOrganizer,\nyear, events", 92.22, "keep"),
    ("Exp 3:\nRelative dates,\nprice edges", 95.56, "keep"),
    ("Exp 4:\nTargeted\nedge cases", 98.61, "keep"),
    ("Exp 5:\nOver-specified\nrules", 97.50, "discard"),
    ("Exp 6:\n3rd few-shot\nexample", 99.17, "keep"),
    ("Exp 7:\nName/location\nrefinement", 99.72, "keep"),
    ("Exp 8:\nDrop trailing\n'location'", 100.00, "keep"),
]

labels = [e[0] for e in experiments]
accuracies = [e[1] for e in experiments]
statuses = [e[2] for e in experiments]

# The "branch tip" accuracy (what was kept)
branch_tip = []
current_best = 74.72
for acc, status in zip(accuracies, statuses):
    if status == "keep":
        current_best = acc
    branch_tip.append(current_best)

# Style — dark background like Karpathy's
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

x = np.arange(len(experiments))

# Plot the branch tip line (kept accuracy)
ax.plot(x, branch_tip, color='#58a6ff', linewidth=2.5, linestyle='--',
        alpha=0.4, zorder=1, label='Branch tip (best kept)')

# Plot all experiment points
for i, (acc, status) in enumerate(zip(accuracies, statuses)):
    if status == "keep" and acc == 100.0:
        # Perfect score — gold star
        ax.scatter(i, acc, color='#ffd700', s=200, zorder=5, marker='*',
                   edgecolors='#ffa500', linewidth=1.5)
    elif status == "keep":
        ax.scatter(i, acc, color='#3fb950', s=100, zorder=4,
                   edgecolors='white', linewidth=0.8)
    else:
        # Discarded — red X
        ax.scatter(i, acc, color='#f85149', s=100, zorder=4,
                   marker='X', edgecolors='white', linewidth=0.8)

# Connect kept experiments with a solid line
kept_x = [i for i, s in enumerate(statuses) if s == "keep"]
kept_acc = [accuracies[i] for i in kept_x]
ax.plot(kept_x, kept_acc, color='#3fb950', linewidth=2.5, zorder=3,
        marker='o', markersize=0)

# Annotations for each point
for i, (label, acc, status) in enumerate(experiments):
    color = '#f85149' if status == 'discard' else '#e6edf3'
    suffix = " (discarded)" if status == 'discard' else ""

    # Position labels to avoid overlap
    if i == 5:  # discarded point
        va, offset = 'top', -8
    elif i >= 7:
        va, offset = 'bottom', 8
    else:
        va, offset = 'bottom', 8

    ax.annotate(f'{acc:.1f}%{suffix}',
                (i, acc), textcoords="offset points",
                xytext=(0, offset), ha='center', va=va,
                fontsize=9, color=color, fontweight='bold')

# Improvement arrows between kept experiments
improvements = [
    (0, 1, "+13.3"),
    (1, 2, "+4.2"),
    (2, 3, "+3.3"),
    (3, 4, "+3.1"),
    (5, 6, "+0.6"),  # skip discarded, show from exp4's position
    (6, 7, "+0.6"),
    (7, 8, "+0.3"),
]

# Shaded region showing improvement from baseline
ax.fill_between(x, 74.72, branch_tip, alpha=0.08, color='#3fb950')

# Add a horizontal line at 100%
ax.axhline(y=100, color='#ffd700', linestyle=':', alpha=0.3, linewidth=1)
ax.text(len(experiments) - 0.5, 100.3, '100% (perfect)', color='#ffd700',
        alpha=0.5, fontsize=8, ha='right')

# Add a horizontal line at baseline
ax.axhline(y=74.72, color='#f85149', linestyle=':', alpha=0.3, linewidth=1)
ax.text(len(experiments) - 0.5, 74.0, 'Baseline: 74.72%', color='#f85149',
        alpha=0.5, fontsize=8, ha='right')

# Formatting
ax.set_xlabel('Experiment', fontsize=12, color='#8b949e', labelpad=10)
ax.set_ylabel('Accuracy (%)', fontsize=12, color='#8b949e', labelpad=10)
ax.set_title('Autoresearch: Prompt Optimization Progress\n'
             'Event Extraction Task — 30 examples, 180 fields — Gemini 2.5 Flash',
             fontsize=14, color='#e6edf3', fontweight='bold', pad=15)

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=7.5, color='#8b949e')
ax.set_ylim(70, 102)
ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0f%%'))
ax.tick_params(colors='#8b949e')

# Grid
ax.grid(True, alpha=0.1, color='#30363d')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#30363d')
ax.spines['bottom'].set_color('#30363d')

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#3fb950',
           markersize=10, label='Kept (improved)', linewidth=0),
    Line2D([0], [0], marker='X', color='w', markerfacecolor='#f85149',
           markersize=10, label='Discarded (regressed)', linewidth=0),
    Line2D([0], [0], marker='*', color='w', markerfacecolor='#ffd700',
           markersize=14, label='Perfect score (100%)', linewidth=0),
]
ax.legend(handles=legend_elements, loc='lower right', framealpha=0.2,
          edgecolor='#30363d', fontsize=9)

# Stats box
stats_text = (
    f"Baseline → Final: 74.72% → 100.00%\n"
    f"Improvement: +25.28 pp\n"
    f"Experiments: 8 (7 kept, 1 discarded)\n"
    f"Cost: $0.00 (Gemini free tier)"
)
props = dict(boxstyle='round,pad=0.5', facecolor='#161b22',
             edgecolor='#30363d', alpha=0.9)
ax.text(0.02, 0.97, stats_text, transform=ax.transAxes, fontsize=8.5,
        verticalalignment='top', bbox=props, color='#8b949e',
        family='monospace')

plt.tight_layout()
plt.savefig('progress.png', dpi=200, facecolor='#0d1117',
            bbox_inches='tight', pad_inches=0.3)
print("Saved progress.png")
