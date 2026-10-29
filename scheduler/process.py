"""Process and event data structures shared by every scheduler."""

from dataclasses import dataclass, field
from typing import Optional

# Event types used by the discrete-event schedulers.
ARRIVAL = "ARR"
DEPARTURE = "DEP"
QUANTUM_EXPIRE = "QUANTUM_EXPIRE"


@dataclass
class Process:
    """A single process in the workload.

    Times are in milliseconds. ``remaining_time`` tracks unfinished CPU work
    for preemptive schedulers; ``start_time`` is the first time the process
    received the CPU, used for response time.
    """

    pid: int
    arrival_time: float
    service_time: float
    priority: int = 10

    remaining_time: float = field(init=False)
    start_time: Optional[float] = field(default=None, init=False)
    completion_time: Optional[float] = field(default=None, init=False)

    def __post_init__(self):
        self.remaining_time = self.service_time

    def fresh_copy(self) -> "Process":
        """Return an unscheduled copy so each algorithm sees the same workload."""
        return Process(self.pid, self.arrival_time, self.service_time, self.priority)


def copy_workload(workload):
    """Copy a workload so simulations never mutate the shared input."""
    return [p.fresh_copy() for p in workload]
