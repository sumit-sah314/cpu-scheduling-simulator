#!/usr/bin/env python3
"""Benchmark every scheduler on the same synthetic workload.

Writes a Markdown report and charts to ``results/``:

    python run_benchmarks.py
    python run_benchmarks.py --processes 5000 --seed 42
"""

import argparse
from pathlib import Path

from scheduler import ALGORITHMS, METRIC_LABELS, compute_metrics, fifo_tick, generate_workload
from scheduler import realtime
from scheduler.classic import round_robin

RESULTS_DIR = Path(__file__).parent / "results"
QUANTUMS_MS = [0.5, 1.0, 2.0, 4.0, 10.0]

# Single-series charts use one hue; text stays in neutral ink.
BAR_COLOR = "#2a78d6"
REFERENCE_COLOR = "#52514e"
TEXT_COLOR = "#0b0b0b"
GRID_COLOR = "#e4e3df"
SURFACE = "#fcfcfb"


def format_value(key, value):
    if key == "cpu_utilization_pct":
        return f"{value:.1f}"
    if key == "total_completion_time_ms":
        return f"{value:g}"
    return f"{value:.2f}"


def markdown_table(header, rows, align="---:"):
    lines = ["| " + " | ".join(header) + " |",
             "| :--- | " + " | ".join(align for _ in header[1:]) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def run(num_processes, seed):
    workload = generate_workload(num_processes=num_processes, seed=seed)
    results = {name: compute_metrics(fn(workload)[0]) for name, fn in ALGORITHMS.items()}

    rr_sweep = {
        q: compute_metrics(round_robin(workload, quantum=q)[0])["avg_waiting_ms"]
        for q in QUANTUMS_MS
    }

    tick_jobs, _, _ = fifo_tick(workload)
    tick_waiting = compute_metrics(tick_jobs)["avg_waiting_ms"]

    rt_rows = []
    for policy, label in [(realtime.RATE_MONOTONIC, "Rate-Monotonic"),
                          (realtime.EARLIEST_DEADLINE_FIRST, "Earliest-Deadline-First")]:
        timeline, misses = realtime.simulate(policy=policy)
        rt_rows.append((label, " ".join(timeline), misses))

    return workload, results, rr_sweep, tick_waiting, rt_rows


def write_report(num_processes, seed, results, rr_sweep, tick_waiting, rt_rows):
    names = list(results)
    fcfs_wait = results["FCFS"]["avg_waiting_ms"]

    metric_rows = [
        [METRIC_LABELS[key]] + [format_value(key, results[n][key]) for n in names]
        for key in METRIC_LABELS
    ]
    rr_rows = [
        [f"{q:g}", f"{w:.2f}", f"{(fcfs_wait - w) / fcfs_wait * 100:.1f}%"]
        for q, w in rr_sweep.items()
    ]

    tasks = realtime.DEFAULT_TASKS
    report = f"""# Benchmark Results

Workload: {num_processes} processes, Poisson arrivals (2 per ms), exponential service times (mean 1 ms), seed {seed}.

## Aperiodic schedulers

{markdown_table(["Metric"] + names, metric_rows)}

![Average waiting time by algorithm](avg_waiting_time.png)

## Round Robin quantum sweep

{markdown_table(["Quantum (ms)", "Avg waiting (ms)", "Reduction vs. FCFS"], rr_rows)}

![Round Robin quantum sweep](rr_quantum_sweep.png)

## Validation

The time-stepped FIFO simulator reports an average waiting time of {tick_waiting:.3f} ms; the event-driven FCFS scheduler reports {fcfs_wait:.3f} ms.

## Real-time schedulers

Tasks (period, execution): {", ".join(f"T{t.task_id}=({t.period}, {t.execution})" for t in tasks)}.
Utilization U = {realtime.utilization(tasks):.4f}; RM bound = {realtime.rm_bound(len(tasks)):.4f}; EDF bound = 1.0000.

{markdown_table(["Policy", "Timeline (1 ms slots)", "Deadline misses"], [[a, b, str(c)] for a, b, c in rt_rows], align=":---")}
"""
    (RESULTS_DIR / "RESULTS.md").write_text(report, encoding="utf-8")
    return report


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_COLOR, labelsize=10)


def plot(results, rr_sweep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401

    # Average waiting time, sorted best to worst.
    ordered = sorted(results.items(), key=lambda kv: kv[1]["avg_waiting_ms"])
    labels = [name for name, _ in ordered]
    values = [m["avg_waiting_ms"] for _, m in ordered]

    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    bars = ax.barh(labels, values, color=BAR_COLOR, height=0.6)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f"{v:.0f} ms" for v in values], padding=4,
                 color=TEXT_COLOR, fontsize=9)
    ax.set_xlabel("Average waiting time (ms) — lower is better", color=TEXT_COLOR)
    ax.set_title("Average waiting time by scheduling algorithm", color=TEXT_COLOR,
                 loc="left", fontsize=12, fontweight="bold")
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(values) * 1.15)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "avg_waiting_time.png", dpi=160)
    plt.close(fig)

    # Round Robin quantum sweep against the FCFS baseline.
    fcfs_wait = results["FCFS"]["avg_waiting_ms"]
    quantums, waits = list(rr_sweep), list(rr_sweep.values())

    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    ax.plot(quantums, waits, color=BAR_COLOR, linewidth=2, marker="o", markersize=7)
    ax.axhline(fcfs_wait, color=REFERENCE_COLOR, linewidth=1.2, linestyle="--")
    ax.annotate(f"FCFS baseline ({fcfs_wait:.0f} ms)", (quantums[0], fcfs_wait),
                textcoords="offset points", xytext=(0, -14), ha="left",
                color=REFERENCE_COLOR, fontsize=9)
    best_q, best_w = quantums[0], waits[0]
    ax.annotate(f"q = {best_q:g} ms: {(fcfs_wait - best_w) / fcfs_wait * 100:.1f}% below FCFS",
                (best_q, best_w), textcoords="offset points", xytext=(10, 8),
                color=TEXT_COLOR, fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks(quantums, [f"{q:g}" for q in quantums])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlabel("Time quantum (ms, log scale)", color=TEXT_COLOR)
    ax.set_ylabel("Average waiting time (ms)", color=TEXT_COLOR)
    ax.set_title("Round Robin: smaller quanta cut average waiting time", color=TEXT_COLOR,
                 loc="left", fontsize=12, fontweight="bold")
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "rr_quantum_sweep.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processes", type=int, default=1000, help="number of processes (default 1000)")
    parser.add_argument("--seed", type=int, default=3360, help="random seed (default 3360)")
    parser.add_argument("--no-plots", action="store_true", help="skip chart generation")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    _, results, rr_sweep, tick_waiting, rt_rows = run(args.processes, args.seed)
    print(write_report(args.processes, args.seed, results, rr_sweep, tick_waiting, rt_rows))
    if not args.no_plots:
        plot(results, rr_sweep)
        print(f"Charts saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
