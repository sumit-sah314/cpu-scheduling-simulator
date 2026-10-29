"""Synthetic workload generation.

Arrivals follow a Poisson process (exponential inter-arrival times with rate
``arrival_rate`` processes/ms) and service times are exponential with mean
``mean_service_time`` ms. Both are sampled by inverse transform and rounded to
whole milliseconds. The first process arrives at t = 0.
"""

import math
import random

from .process import Process

DEFAULT_NUM_PROCESSES = 1000
DEFAULT_ARRIVAL_RATE = 2.0        # processes per ms
DEFAULT_MEAN_SERVICE_TIME = 1.0   # ms
DEFAULT_SEED = 3360
DEFAULT_PRIORITY_SEED = 4404


def _uniform_nonzero(rng):
    """Uniform(0, 1) sample that is never 0, so log(u) is defined."""
    u = rng.random()
    while u == 0:
        u = rng.random()
    return u


def generate_workload(
    num_processes=DEFAULT_NUM_PROCESSES,
    arrival_rate=DEFAULT_ARRIVAL_RATE,
    mean_service_time=DEFAULT_MEAN_SERVICE_TIME,
    seed=DEFAULT_SEED,
    priority_seed=DEFAULT_PRIORITY_SEED,
):
    """Generate a reproducible list of processes.

    Priorities (1 = highest, 10 = lowest) come from a separate random stream so
    that adding priorities never changes the arrival and service times.
    """
    rng = random.Random(seed)
    processes = []
    arrival_time = 0

    for pid in range(1, num_processes + 1):
        if pid > 1:
            u = _uniform_nonzero(rng)
            arrival_time += round(-math.log(u) / arrival_rate)

        u = _uniform_nonzero(rng)
        service_time = round(-math.log(u) * mean_service_time)

        processes.append(Process(pid, arrival_time, service_time))

    priority_rng = random.Random(priority_seed)
    for p in processes:
        p.priority = priority_rng.randint(1, 10)

    return processes
