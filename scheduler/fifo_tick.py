"""Time-stepped FIFO simulator: a 1 kHz CPU where each loop iteration is 1 ms.

This is the baseline the event-driven simulators are validated against: it
advances the clock tick by tick, tracks process states
(NEW -> READY -> RUNNING -> TERMINATED), and records a compact CPU trace of
BUSY/IDLE intervals.
"""

from collections import deque

from .process import copy_workload


def _append_trace(trace, start, end, status, pid=None):
    """Merge consecutive ticks with the same status/PID into one interval."""
    if start == end:
        return
    if trace and trace[-1][2] == status and trace[-1][3] == pid:
        trace[-1] = (trace[-1][0], end, status, pid)
    else:
        trace.append((start, end, status, pid))


def fifo_tick(workload):
    """Simulate FIFO scheduling one millisecond at a time.

    Returns ``(jobs, trace, total_time)`` where trace holds
    ``(start, end, "BUSY" | "IDLE", pid)`` intervals.
    """
    jobs = copy_workload(workload)
    states = {p.pid: "NEW" for p in jobs}
    ready_queue = deque()
    trace = []
    current = None
    remaining = 0
    clock = 0
    next_arrival = 0
    completed = 0

    while completed < len(jobs):
        while next_arrival < len(jobs) and jobs[next_arrival].arrival_time <= clock:
            states[jobs[next_arrival].pid] = "READY"
            ready_queue.append(jobs[next_arrival])
            next_arrival += 1

        # Dispatch; the loop also completes any zero-length jobs immediately.
        while current is None and ready_queue:
            current = ready_queue.popleft()
            states[current.pid] = "RUNNING"
            current.start_time = clock
            remaining = current.service_time
            if remaining == 0:
                current.completion_time = clock
                states[current.pid] = "TERMINATED"
                completed += 1
                current = None

        if completed == len(jobs):
            break

        if current is None:
            _append_trace(trace, clock, clock + 1, "IDLE")
        else:
            _append_trace(trace, clock, clock + 1, "BUSY", current.pid)
            remaining -= 1
            if remaining == 0:
                current.completion_time = clock + 1
                states[current.pid] = "TERMINATED"
                completed += 1
                current = None

        clock += 1

    for p in jobs:
        p.remaining_time = 0
    return jobs, trace, clock
