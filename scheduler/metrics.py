"""Performance metrics computed from a completed simulation."""


def compute_metrics(jobs):
    """Return scheduling metrics (times in ms) for a list of finished processes."""
    n = len(jobs)
    total_time = max(p.completion_time for p in jobs)
    busy_time = sum(p.service_time for p in jobs)

    turnaround = [p.completion_time - p.arrival_time for p in jobs]
    waiting = [t - p.service_time for t, p in zip(turnaround, jobs)]
    response = [p.start_time - p.arrival_time for p in jobs]

    return {
        "total_completion_time_ms": total_time,
        "avg_turnaround_ms": sum(turnaround) / n,
        "avg_waiting_ms": sum(waiting) / n,
        "avg_response_ms": sum(response) / n,
        "max_waiting_ms": max(waiting),
        "cpu_utilization_pct": busy_time / total_time * 100,
        "throughput_per_s": n / (total_time / 1000),
        # Little's law: average number of processes waiting in the ready queue.
        "avg_ready_queue_length": sum(waiting) / total_time,
    }


METRIC_LABELS = {
    "total_completion_time_ms": "Total completion time (ms)",
    "avg_turnaround_ms": "Avg turnaround time (ms)",
    "avg_waiting_ms": "Avg waiting time (ms)",
    "avg_response_ms": "Avg response time (ms)",
    "max_waiting_ms": "Max waiting time (ms)",
    "cpu_utilization_pct": "CPU utilization (%)",
    "throughput_per_s": "Throughput (processes/s)",
    "avg_ready_queue_length": "Avg ready queue length",
}
