"""Classic discrete-event CPU schedulers: FCFS, SJF, SRTF, Round Robin, HRRN.

Each scheduler returns ``(jobs, timeline)`` where ``jobs`` are the finished
processes and ``timeline`` is a list of ``(pid, start, end)`` CPU intervals.
Simulated time jumps from one event to the next instead of ticking.
"""

from .events import EventQueue
from .process import ARRIVAL, DEPARTURE, QUANTUM_EXPIRE, copy_workload


def _run_non_preemptive(workload, select):
    """Shared event loop for non-preemptive policies.

    ``select(ready_queue, clock)`` picks the next process to dispatch; once
    dispatched, a process runs until it completes.
    """
    jobs = copy_workload(workload)
    events = EventQueue()
    for p in jobs:
        events.push(p.arrival_time, ARRIVAL, p)

    ready_queue = []
    cpu = None
    timeline = []

    while events:
        clock = events.peek_time()

        for _, event_type, process in events.pop_all_at(clock):
            if event_type == ARRIVAL:
                ready_queue.append(process)
            elif event_type == DEPARTURE:
                process.completion_time = clock
                process.remaining_time = 0
                cpu = None

        if cpu is None and ready_queue:
            cpu = select(ready_queue, clock)
            ready_queue.remove(cpu)
            cpu.start_time = clock
            finish_time = clock + cpu.service_time
            timeline.append((cpu.pid, clock, finish_time))
            events.push(finish_time, DEPARTURE, cpu)

    return jobs, timeline


def fcfs(workload):
    """First-Come, First-Served: dispatch in arrival order."""
    return _run_non_preemptive(workload, lambda ready, clock: ready[0])


def sjf(workload):
    """Shortest Job First (non-preemptive): shortest service time, ties by PID."""
    return _run_non_preemptive(
        workload, lambda ready, clock: min(ready, key=lambda p: (p.service_time, p.pid))
    )


def _response_ratio(process, clock):
    if process.service_time == 0:
        return float("inf")
    waiting = clock - process.arrival_time
    return (waiting + process.service_time) / process.service_time


def hrrn(workload):
    """Highest Response Ratio Next: maximize (W + S) / S, ties by lowest PID.

    The ratio grows as a process waits, so long jobs age toward the front
    instead of starving.
    """
    return _run_non_preemptive(
        workload,
        lambda ready, clock: max(ready, key=lambda p: (_response_ratio(p, clock), -p.pid)),
    )


def srtf(workload):
    """Shortest Remaining Time First: preemptive SJF.

    When a newly ready process has less remaining work than the running one,
    the running process is preempted and its pending departure is cancelled.
    """
    jobs = copy_workload(workload)
    events = EventQueue({DEPARTURE: 0, ARRIVAL: 1})
    for p in jobs:
        events.push(p.arrival_time, ARRIVAL, p)

    ready_queue = []
    cpu = None
    last_update = 0
    run_start = 0
    timeline = []

    def shortest(queue):
        return min(queue, key=lambda p: (p.remaining_time, p.pid))

    while events:
        clock = events.peek_time()

        # Charge the running process for the time since the last event.
        if cpu is not None:
            cpu.remaining_time -= clock - last_update
            last_update = clock

        for _, event_type, process in events.pop_all_at(clock):
            if event_type == ARRIVAL:
                ready_queue.append(process)
            elif event_type == DEPARTURE:
                if clock > run_start:
                    timeline.append((cpu.pid, run_start, clock))
                process.completion_time = clock
                process.remaining_time = 0
                cpu = None

        # Preempt if a ready process has strictly less remaining work.
        if cpu is not None and ready_queue:
            candidate = shortest(ready_queue)
            if candidate.remaining_time < cpu.remaining_time:
                if clock > run_start:
                    timeline.append((cpu.pid, run_start, clock))
                events.remove_departure(cpu)
                ready_queue.append(cpu)
                cpu = None

        if cpu is None and ready_queue:
            cpu = shortest(ready_queue)
            ready_queue.remove(cpu)
            if cpu.start_time is None:
                cpu.start_time = clock
            run_start = clock
            last_update = clock
            events.push(clock + cpu.remaining_time, DEPARTURE, cpu)

    return jobs, timeline


def round_robin(workload, quantum=2.0):
    """Round Robin with a fixed time quantum (ms).

    A process runs for at most one quantum, then returns to the back of the
    FIFO ready queue. Arrivals at the same instant are queued before the
    preempted process.
    """
    jobs = copy_workload(workload)
    events = EventQueue({ARRIVAL: 0, DEPARTURE: 1, QUANTUM_EXPIRE: 1})
    for p in jobs:
        events.push(p.arrival_time, ARRIVAL, p)

    ready_queue = []
    cpu = None
    last_start = 0
    timeline = []

    while events:
        clock = events.peek_time()

        for _, event_type, process in events.pop_all_at(clock):
            if event_type == ARRIVAL:
                ready_queue.append(process)
            elif event_type == DEPARTURE:
                cpu.remaining_time = 0
                cpu.completion_time = clock
                timeline.append((cpu.pid, last_start, clock))
                cpu = None
            elif event_type == QUANTUM_EXPIRE:
                cpu.remaining_time -= clock - last_start
                timeline.append((cpu.pid, last_start, clock))
                ready_queue.append(cpu)
                cpu = None

        if cpu is None and ready_queue:
            cpu = ready_queue.pop(0)
            if cpu.start_time is None:
                cpu.start_time = clock
            last_start = clock

            if cpu.remaining_time <= quantum:
                events.push(clock + cpu.remaining_time, DEPARTURE, cpu)
            else:
                events.push(clock + quantum, QUANTUM_EXPIRE, cpu)

    return jobs, timeline
