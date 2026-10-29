"""Real-time scheduling of periodic tasks: Rate-Monotonic (RM) and Earliest-Deadline-First (EDF).

Tasks have implicit deadlines (deadline = next release) and are simulated in
1 ms ticks over one hyper-period on a single preemptive CPU.
"""

from dataclasses import dataclass
from functools import reduce
from math import gcd

RATE_MONOTONIC = "RM"
EARLIEST_DEADLINE_FIRST = "EDF"


@dataclass(frozen=True)
class PeriodicTask:
    task_id: int
    period: int
    execution: int


DEFAULT_TASKS = [
    PeriodicTask(1, period=4, execution=1),
    PeriodicTask(2, period=6, execution=2),
    PeriodicTask(3, period=12, execution=3),
]


def utilization(tasks):
    """Total CPU utilization U = sum(C_i / T_i)."""
    return sum(t.execution / t.period for t in tasks)


def rm_bound(n):
    """Liu & Layland sufficient bound for RM: n(2^(1/n) - 1)."""
    return n * (2 ** (1 / n) - 1)


def hyperperiod(tasks):
    """Least common multiple of all task periods."""
    return reduce(lambda a, b: a * b // gcd(a, b), (t.period for t in tasks))


def simulate(tasks=DEFAULT_TASKS, policy=RATE_MONOTONIC, duration=None):
    """Run RM or EDF for ``duration`` ms (default: one hyper-period).

    Returns ``(timeline, deadline_misses)`` where timeline holds "T<id>" or
    "Idle" for each millisecond.
    """
    duration = duration or hyperperiod(tasks)
    if policy == RATE_MONOTONIC:
        # Static priority: shorter period wins.
        def key(job):
            return (job["period"], job["release"], job["task_id"])
    elif policy == EARLIEST_DEADLINE_FIRST:
        # Dynamic priority: earliest absolute deadline wins.
        def key(job):
            return (job["deadline"], job["release"], job["task_id"])
    else:
        raise ValueError(f"Unknown scheduling policy: {policy}")

    jobs = []
    timeline = []

    for time in range(duration):
        for task in tasks:
            if time % task.period == 0:
                jobs.append({
                    "task_id": task.task_id,
                    "period": task.period,
                    "release": time,
                    "deadline": time + task.period,
                    "remaining": task.execution,
                    "finish": None,
                })

        ready = [job for job in jobs if job["remaining"] > 0]
        if not ready:
            timeline.append("Idle")
            continue

        running = min(ready, key=key)
        running["remaining"] -= 1
        timeline.append(f"T{running['task_id']}")
        if running["remaining"] == 0:
            running["finish"] = time + 1

    misses = sum(
        1 for job in jobs if job["finish"] is None or job["finish"] > job["deadline"]
    )
    return timeline, misses
