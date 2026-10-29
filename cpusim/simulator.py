"""Event-driven CPU scheduling simulator (FCFS, SJF, SRTF, RR, HRRN, Priority)."""
import heapq
import itertools
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

ARRIVAL, COMPLETION, QUANTUM = 1, 0, 2  # value = ordering among same-time events


@dataclass
class Process:
    pid: int
    arrival: int
    burst: int
    priority: int = 0
    remaining: int = field(init=False)
    start: Optional[int] = field(default=None, init=False)
    finish: Optional[int] = field(default=None, init=False)

    def __post_init__(self):
        if self.burst <= 0 or self.arrival < 0:
            raise ValueError("burst must be > 0 and arrival >= 0")
        self.remaining = self.burst

    @property
    def turnaround(self):
        return self.finish - self.arrival

    @property
    def waiting(self):
        return self.turnaround - self.burst

    @property
    def response(self):
        return self.start - self.arrival


class Policy:
    """Ready-queue policy backed by a priority queue (heap)."""
    name = ""
    preemptive = False
    quantum: Optional[int] = None

    def __init__(self):
        self._heap: List[Tuple] = []
        self._seq = itertools.count()

    def key(self, p: Process, now: int):
        raise NotImplementedError

    def add(self, p: Process, now: int):
        heapq.heappush(self._heap, (self.key(p, now), next(self._seq), p))

    def peek(self, now: int) -> Optional[Process]:
        return self._heap[0][2] if self._heap else None

    def pop(self, now: int) -> Process:
        return heapq.heappop(self._heap)[2]

    def should_preempt(self, running: Process, now: int) -> bool:
        if not self.preemptive or not self._heap:
            return False
        return self.key(self.peek(now), now) < self.key(running, now)

    def __len__(self):
        return len(self._heap)


class FCFS(Policy):
    name = "FCFS"

    def key(self, p, now):
        return (p.arrival,)


class SJF(Policy):
    name = "SJF"

    def key(self, p, now):
        return (p.burst, p.arrival)


class SRTF(Policy):
    name = "SRTF"
    preemptive = True

    def key(self, p, now):
        return (p.remaining, p.arrival)


class Priority(Policy):
    """Lower number = higher priority; preemptive."""
    name = "PRIORITY"
    preemptive = True

    def key(self, p, now):
        return (p.priority, p.arrival)


class RoundRobin(Policy):
    name = "RR"

    def __init__(self, quantum: int = 4):
        super().__init__()
        if quantum <= 0:
            raise ValueError("quantum must be > 0")
        self.quantum = quantum

    def key(self, p, now):
        return ()  # FIFO by insertion sequence


class HRRN(Policy):
    """Highest response ratio next; ratio changes with time so scan the queue."""
    name = "HRRN"

    def key(self, p, now):
        return (-((now - p.arrival) + p.burst) / p.burst, p.arrival)

    def peek(self, now):
        return min(self._heap, key=lambda e: (self.key(e[2], now), e[1]))[2] if self._heap else None

    def pop(self, now):
        best = self.peek(now)
        self._heap = [e for e in self._heap if e[2] is not best]
        heapq.heapify(self._heap)
        return best


POLICIES: Dict[str, Callable[..., Policy]] = {
    "fcfs": FCFS, "sjf": SJF, "srtf": SRTF, "rr": RoundRobin,
    "hrrn": HRRN, "priority": Priority,
}


@dataclass
class Result:
    policy: str
    processes: List[Process]
    gantt: List[Tuple[int, int, Optional[int]]]  # (start, end, pid or None=idle)
    context_switches: int
    end_time: int

    def _avg(self, attr):
        return sum(getattr(p, attr) for p in self.processes) / len(self.processes)

    @property
    def avg_waiting(self): return self._avg("waiting")

    @property
    def avg_turnaround(self): return self._avg("turnaround")

    @property
    def avg_response(self): return self._avg("response")

    @property
    def cpu_utilization(self):
        busy = sum(e - s for s, e, pid in self.gantt if pid is not None)
        return busy / self.end_time if self.end_time else 0.0


def simulate(processes: List[Process], policy: Policy) -> Result:
    procs = [Process(p.pid, p.arrival, p.burst, p.priority) for p in processes]
    events: List[Tuple] = []
    seq = itertools.count()

    def push(t, kind, payload):
        heapq.heappush(events, (t, kind, next(seq), payload))

    for p in procs:
        push(p.arrival, ARRIVAL, p)

    running: Optional[Process] = None
    run_start = 0
    gen = 0  # dispatch generation; invalidates stale completion/quantum events
    gantt: List[Tuple[int, int, Optional[int]]] = []
    switches = 0
    last_pid: Optional[int] = None
    idle_since: Optional[int] = 0

    def log(s, e, pid):
        if e <= s:
            return
        if gantt and gantt[-1][2] == pid and gantt[-1][1] == s:
            gantt[-1] = (gantt[-1][0], e, pid)
        else:
            gantt.append((s, e, pid))

    def stop_running(now):
        nonlocal running, gen
        running.remaining -= now - run_start
        log(run_start, now, running.pid)
        p, running = running, None
        gen += 1
        return p

    now = 0
    while events:
        now = events[0][0]
        while events and events[0][0] == now:
            _, kind, _, payload = heapq.heappop(events)
            if kind == ARRIVAL:
                policy.add(payload, now)
            elif payload[1] != gen:
                continue
            elif kind == COMPLETION:
                p = stop_running(now)
                p.finish = now
            elif kind == QUANTUM:
                policy.add(stop_running(now), now)
        if running is not None and policy.should_preempt(running, now):
            policy.add(stop_running(now), now)
        if running is None and policy.peek(now) is not None:
            if idle_since is not None:
                log(idle_since, now, None)
                idle_since = None
            running = policy.pop(now)
            run_start = now
            if running.start is None:
                running.start = now
            if last_pid != running.pid:
                switches += 1
            last_pid = running.pid
            push(now + running.remaining, COMPLETION, (running, gen))
            if policy.quantum and running.remaining > policy.quantum:
                push(now + policy.quantum, QUANTUM, (running, gen))
        if running is None and idle_since is None:
            idle_since = now
    return Result(policy.name, procs, gantt, switches, now)


def generate_workload(n=1000, seed=0, max_arrival=5000, max_burst=50, max_priority=10):
    rng = random.Random(seed)
    return [Process(i, rng.randint(0, max_arrival), rng.randint(1, max_burst),
                    rng.randint(0, max_priority)) for i in range(n)]
