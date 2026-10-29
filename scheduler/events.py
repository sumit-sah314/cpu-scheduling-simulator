"""A priority-queue-backed event queue for discrete-event simulation."""

import heapq
import itertools

from .process import ARRIVAL, DEPARTURE


class EventQueue:
    """Min-heap of (time, tie-break, pid) ordered events.

    ``type_order`` maps an event type to its rank when several events share a
    timestamp, which lets each scheduler define how simultaneous arrivals,
    departures, and quantum expirations are ordered.
    """

    def __init__(self, type_order=None):
        self._heap = []
        self._counter = itertools.count()
        self._type_order = type_order or {DEPARTURE: 0, ARRIVAL: 1}

    def push(self, time, event_type, process):
        rank = self._type_order.get(event_type, len(self._type_order))
        heapq.heappush(
            self._heap,
            (time, rank, process.pid, next(self._counter), event_type, process),
        )

    def pop(self):
        time, _, _, _, event_type, process = heapq.heappop(self._heap)
        return time, event_type, process

    def peek_time(self):
        return self._heap[0][0]

    def remove_departure(self, process):
        """Cancel a scheduled departure (used when a running process is preempted)."""
        for i, entry in enumerate(self._heap):
            if entry[4] == DEPARTURE and entry[5] is process:
                self._heap[i] = self._heap[-1]
                self._heap.pop()
                heapq.heapify(self._heap)
                return

    def pop_all_at(self, time):
        """Pop every event scheduled at exactly ``time``, in tie-break order."""
        batch = []
        while self._heap and self._heap[0][0] == time:
            batch.append(self.pop())
        return batch

    def __bool__(self):
        return bool(self._heap)

    def __len__(self):
        return len(self._heap)
