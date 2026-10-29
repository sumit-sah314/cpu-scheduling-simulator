"""CPU scheduling and process control simulator."""

from .advanced import effective_priority, mlfq, priority_with_aging
from .classic import fcfs, hrrn, round_robin, sjf, srtf
from .fifo_tick import fifo_tick
from .metrics import METRIC_LABELS, compute_metrics
from .process import Process
from .workload import generate_workload

ALGORITHMS = {
    "FCFS": fcfs,
    "SJF": sjf,
    "SRTF": srtf,
    "RR (q=2 ms)": lambda w: round_robin(w, quantum=2.0),
    "HRRN": hrrn,
    "Priority + Aging": priority_with_aging,
    "MLFQ": mlfq,
}

__all__ = [
    "ALGORITHMS",
    "METRIC_LABELS",
    "Process",
    "compute_metrics",
    "effective_priority",
    "fcfs",
    "fifo_tick",
    "generate_workload",
    "hrrn",
    "mlfq",
    "priority_with_aging",
    "round_robin",
    "sjf",
    "srtf",
]
