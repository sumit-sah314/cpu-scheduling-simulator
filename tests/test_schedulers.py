"""Correctness tests for the CPU scheduling simulator."""

import pytest

from scheduler import (
    ALGORITHMS,
    Process,
    compute_metrics,
    effective_priority,
    fcfs,
    fifo_tick,
    generate_workload,
    hrrn,
    mlfq,
    priority_with_aging,
    round_robin,
    sjf,
    srtf,
)
from scheduler import realtime


@pytest.fixture(scope="module")
def workload():
    return generate_workload()


def small_workload():
    return [Process(1, 0, 5), Process(2, 1, 2), Process(3, 2, 1)]


# ---------- hand-checkable examples ----------

def test_fcfs_runs_in_arrival_order():
    _, timeline = fcfs(small_workload())
    assert timeline == [(1, 0, 5), (2, 5, 7), (3, 7, 8)]


def test_sjf_picks_shortest_waiting_job():
    _, timeline = sjf(small_workload())
    assert timeline == [(1, 0, 5), (3, 5, 6), (2, 6, 8)]


def test_srtf_preempts_longer_job():
    jobs, _ = srtf(small_workload())
    finish = {p.pid: p.completion_time for p in jobs}
    # P2 arrives at t=1 with 2 ms of work vs P1's 4 remaining, so it preempts.
    assert finish == {1: 8, 2: 3, 3: 4}


def test_round_robin_large_quantum_matches_fcfs():
    rr_jobs, _ = round_robin(small_workload(), quantum=100)
    fcfs_jobs, _ = fcfs(small_workload())
    assert [p.completion_time for p in rr_jobs] == [p.completion_time for p in fcfs_jobs]


def test_aging_improves_priority_over_time():
    p = Process(2, 0, 2, priority=8)
    assert [effective_priority(p, t) for t in (0, 10, 15, 25)] == [8, 8, 7, 6]


def test_aging_never_exceeds_top_priority():
    assert effective_priority(Process(1, 0, 1, priority=3), 10_000) == 1


def test_priority_with_aging_example():
    jobs, _ = priority_with_aging(
        [Process(1, 0, 15, 1), Process(2, 0, 2, 8), Process(3, 5, 2, 7)]
    )
    assert {p.pid: (p.start_time, p.completion_time) for p in jobs} == {
        1: (0, 15), 2: (15, 17), 3: (17, 19)
    }


def test_mlfq_demotes_long_job_and_favors_short_ones():
    jobs, _ = mlfq([Process(1, 0, 25, 5), Process(2, 1, 1, 5), Process(3, 4, 1, 5)])
    assert {p.pid: (p.start_time, p.completion_time) for p in jobs} == {
        1: (0, 27), 2: (2, 3), 3: (4, 5)
    }


def test_hrrn_prefers_long_waiting_job():
    # P2 has waited 10 ms for a 1 ms job (ratio 11); P3 just arrived (ratio 1).
    jobs, timeline = hrrn([Process(1, 0, 10), Process(2, 0, 1), Process(3, 10, 1)])
    assert timeline[1][0] == 2


# ---------- invariants on the full 1,000-process workload ----------

@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_every_process_completes_after_arriving(workload, name):
    jobs, _ = ALGORITHMS[name](workload)
    assert len(jobs) == 1000
    for p in jobs:
        assert p.completion_time is not None
        assert p.start_time >= p.arrival_time
        assert p.completion_time >= p.start_time


@pytest.mark.parametrize("name", list(ALGORITHMS))
def test_work_conserving_schedulers_finish_together(workload, name):
    # Every policy here is work-conserving, so the makespan is identical.
    jobs, _ = ALGORITHMS[name](workload)
    assert compute_metrics(jobs)["total_completion_time_ms"] == 955


def test_inputs_are_not_mutated(workload):
    fcfs(workload)
    assert all(p.start_time is None for p in workload)


def test_tick_and_event_simulators_agree(workload):
    tick_jobs, _, total_time = fifo_tick(workload)
    event_jobs, _ = fcfs(workload)
    assert total_time == 955
    assert compute_metrics(tick_jobs)["avg_waiting_ms"] == pytest.approx(
        compute_metrics(event_jobs)["avg_waiting_ms"]
    )


def test_srtf_never_waits_longer_than_sjf_on_average(workload):
    assert (
        compute_metrics(srtf(workload)[0])["avg_waiting_ms"]
        <= compute_metrics(sjf(workload)[0])["avg_waiting_ms"]
    )


def test_reference_results(workload):
    """Regression check against the original analysis."""
    expected_waiting = {
        "FCFS": 286.863,
        "SJF": 87.997,
        "SRTF": 87.951,
        "RR (q=2 ms)": 270.811,
        "HRRN": 106.319,
        "Priority + Aging": 285.803,
        "MLFQ": 270.351,
    }
    for name, value in expected_waiting.items():
        got = compute_metrics(ALGORITHMS[name](workload)[0])["avg_waiting_ms"]
        assert got == pytest.approx(value, abs=1e-3), name


# ---------- real-time scheduling ----------

def test_realtime_utilization_and_bounds():
    assert realtime.utilization(realtime.DEFAULT_TASKS) == pytest.approx(5 / 6)
    assert realtime.rm_bound(3) == pytest.approx(0.7798, abs=1e-4)
    assert realtime.hyperperiod(realtime.DEFAULT_TASKS) == 12


@pytest.mark.parametrize("policy", [realtime.RATE_MONOTONIC, realtime.EARLIEST_DEADLINE_FIRST])
def test_realtime_meets_all_deadlines(policy):
    timeline, misses = realtime.simulate(policy=policy)
    assert misses == 0
    assert len(timeline) == 12
    assert timeline.count("Idle") == 2  # 1 - U = 1/6 of 12 ms


def test_realtime_overloaded_task_set_misses_deadlines():
    overloaded = [realtime.PeriodicTask(1, 2, 2), realtime.PeriodicTask(2, 4, 1)]
    _, misses = realtime.simulate(overloaded, policy=realtime.EARLIEST_DEADLINE_FIRST)
    assert misses > 0
