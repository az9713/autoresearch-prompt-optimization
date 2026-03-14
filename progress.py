"""
Reads results.tsv and renders an ASCII chart of accuracy over experiments.
Usage: python progress.py
"""

import csv
from pathlib import Path

RESULTS_FILE = Path(__file__).parent / "results.tsv"
CHART_WIDTH = 60
CHART_HEIGHT = 15


def main():
    if not RESULTS_FILE.exists():
        print("No results.tsv found. Run some experiments first.")
        return

    rows = []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                acc = float(row["accuracy"])
                rows.append({
                    "commit": row["commit"],
                    "accuracy": acc,
                    "status": row["status"],
                    "description": row["description"],
                })
            except (ValueError, KeyError):
                continue

    if not rows:
        print("No experiment data in results.tsv yet.")
        return

    # Extract data
    accuracies = [r["accuracy"] for r in rows]
    best_kept = []
    current_best = 0.0
    for r in rows:
        if r["status"] == "keep":
            current_best = max(current_best, r["accuracy"])
        best_kept.append(current_best)

    # Chart bounds
    min_acc = max(0, min(accuracies) - 5)
    max_acc = min(100, max(accuracies) + 5)
    if max_acc == min_acc:
        max_acc = min_acc + 10
    acc_range = max_acc - min_acc

    # Build ASCII chart
    print()
    print(f"  Prompt Optimizer Progress — {len(rows)} experiments")
    print(f"  {'=' * (CHART_WIDTH + 8)}")

    # Create grid
    grid = [[" " for _ in range(CHART_WIDTH)] for _ in range(CHART_HEIGHT)]

    # Plot points
    for i, acc in enumerate(accuracies):
        x = int(i / max(len(accuracies) - 1, 1) * (CHART_WIDTH - 1))
        y = int((acc - min_acc) / acc_range * (CHART_HEIGHT - 1))
        y = max(0, min(CHART_HEIGHT - 1, y))
        status = rows[i]["status"]
        if status == "keep":
            grid[y][x] = "#"
        elif status == "discard":
            grid[y][x] = "."
        else:
            grid[y][x] = "x"

    # Plot best-kept line
    for i, best in enumerate(best_kept):
        x = int(i / max(len(best_kept) - 1, 1) * (CHART_WIDTH - 1))
        y = int((best - min_acc) / acc_range * (CHART_HEIGHT - 1))
        y = max(0, min(CHART_HEIGHT - 1, y))
        if grid[y][x] == " ":
            grid[y][x] = "-"

    # Render
    for row_idx in range(CHART_HEIGHT - 1, -1, -1):
        acc_label = min_acc + (row_idx / (CHART_HEIGHT - 1)) * acc_range
        print(f"  {acc_label:5.1f}% |{''.join(grid[row_idx])}|")

    print(f"        +{'-' * CHART_WIDTH}+")

    # X-axis labels
    print(f"         1{' ' * (CHART_WIDTH - len(str(len(rows))) - 1)}{len(rows)}")
    print(f"         {'experiments':^{CHART_WIDTH}}")

    # Legend
    print()
    print(f"  Legend:  # = kept (improved)   . = discarded   x = crash   - = best so far")

    # Summary stats
    kept = [r for r in rows if r["status"] == "keep"]
    discarded = [r for r in rows if r["status"] == "discard"]
    crashed = [r for r in rows if r["status"] == "crash"]

    print()
    print(f"  Baseline:    {rows[0]['accuracy']:.2f}%")
    print(f"  Best:        {max(accuracies):.2f}%")
    print(f"  Current:     {best_kept[-1]:.2f}%")
    print(f"  Improvement: +{best_kept[-1] - rows[0]['accuracy']:.2f}%")
    print()
    print(f"  Kept: {len(kept)}  |  Discarded: {len(discarded)}  |  Crashed: {len(crashed)}  |  Total: {len(rows)}")

    # Recent experiments
    print()
    print(f"  Last 5 experiments:")
    for r in rows[-5:]:
        marker = {"keep": "+", "discard": "-", "crash": "!"}[r["status"]]
        print(f"    [{marker}] {r['accuracy']:5.1f}%  {r['commit']}  {r['description'][:50]}")

    print()


if __name__ == "__main__":
    main()
