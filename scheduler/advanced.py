"""Advanced schedulers: Priority Scheduling with Aging and a two-level MLFQ."""

import math
from collections import deque

from .process import copy_workload

AGING_INTERVAL_MS = 10
MLFQ_Q0_QUANTUM_MS = 2
MLFQ_BOOST_INTERVAL_MS = 20


def effective_priority(process, clock, aging_interval=AGING_INTERVAL_MS):
    """Priority after aging (1 = highest).

    A process gains one priority level for each full ``aging_interval`` it has
    waited beyond the first, and can never rise above priority 1.
    """
    waited = clock - process.arrival_time
    aging_steps = max(0, math.ceil(waited / aging_interval) - 1)
    return max(1, process.priority - aging_steps)


def priority_with_aging(workload, aging_interval=AGING_INTERVAL_MS):
    """Non-preemptive priority scheduling with aging to prevent starvation.

    Returns ``(jobs, timeline)``. Ties on effective priority go to the lowest PID.
    """
    jobs = sorted(copy_workload(workload), key=lambda p: (p.arrival_time, p.pid))
    ready_queue = []
    clock = 0
    next_arrival = 0
    completed = 0
    timeline = []

    while completed < len(jobs):
        # Idle CPU: jump straight to the next arrival.
        if not ready_queue and next_arrival < len(jobs):
            clock = max(clock, jobs[next_arrival].arrival_time)

        while next_arrival < len(jobs) and jobs[next_arrival].arrival_time <= clock:
            ready_queue.append(jobs[next_arrival])
            next_arrival += 1

        running = min(
            ready_queue,
            key=lambda p: (effective_priority(p, clock, aging_interval), p.pid),
        )
        ready_queue.remove(running)

        running.start_time = clock
        timeline.append((running.pid, clock, clock + running.service_time))
        clock += running.service_time
        running.completion_time = clock
        running.remaining_time = 0
        completed += 1

    return jobs, timeline


def mlfq(
    workload,
    q0_quantum=MLFQ_Q0_QUANTUM_MS,
    boost_interval=MLFQ_BOOST_INTERVAL_MS,
):
    """Two-level Multilevel Feedback Queue with periodic priority boosting.

    * Q0 (high priority): Round Robin with a ``q0_quantum`` ms quantum.
      New arrivals enter Q0; a process that uses its full quantum is demoted.
    * Q1 (low priority): FCFS, preempted whenever Q0 has work.
    * Every ``boost_interval`` ms all Q1 processes move back to Q0 so
      CPU-bound jobs cannot starve.

    Simulated in 1 ms ticks. Returns ``(jobs, history)`` where history holds
    ``(start, end, pid, queue_level)`` per tick.
    """
    jobs = sorted(copy_workload(workload), key=lambda p: (p.arrival_time, p.pid))

    q0, q1 = deque(), deque()
    time = 0
    next_arrival = 0
    finished = 0
    running = None
    level = None
    quantum_used = 0
    history = []

    while finished < len(jobs):
        # 1. Admit new arrivals into Q0.
        while next_arrival < len(jobs) and jobs[next_arrival].arrival_time <= time:
            q0.append(jobs[next_arrival])
            next_arrival += 1

        # 2. Periodic priority boost: everything in Q1 returns to Q0.
        if time > 0 and time % boost_interval == 0:
            if running is not None and level == 1:
                q1.appendleft(running)
                running = None
            while q1:
                q0.append(q1.popleft())
            if running is not None and level == 0:
                quantum_used = 0

        # 3. Q0 work preempts a running Q1 process.
        if running is not None and level == 1 and q0:
            q1.appendleft(running)
            running = None

        # 4. Dispatch from the highest non-empty queue.
        if running is None:
            if q0:
                running, level, quantum_used = q0.popleft(), 0, 0
            elif q1:
                running, level = q1.popleft(), 1
            else:
                time += 1
                continue
            if running.start_time is None:
                running.start_time = time

        # Zero-length jobs finish the moment they are dispatched.
        if running.remaining_time == 0:
            running.completion_time = time
            finished += 1
            running = None
            continue

        # 5. Run for one 1 ms tick.
        history.append((time, time + 1, running.pid, level))
        running.remaining_time -= 1
        if level == 0:
            quantum_used += 1
        time += 1

        # 6. Complete, or demote after a full Q0 quantum.
        if running.remaining_time == 0:
            running.completion_time = time
            finished += 1
            running = None
        elif level == 0 and quantum_used == q0_quantum:
            q1.append(running)
            running = None

    return jobs, history
