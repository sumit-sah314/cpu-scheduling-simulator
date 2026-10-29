import unittest

from cpusim.simulator import (FCFS, HRRN, SJF, SRTF, POLICIES, Process,
                              RoundRobin, generate_workload, simulate)


def P(*rows):
    return [Process(i, a, b) for i, (a, b) in enumerate(rows)]


def finishes(r):
    return [p.finish for p in r.processes]


class TestSimulator(unittest.TestCase):
    def test_fcfs(self):
        self.assertEqual(finishes(simulate(P((0, 5), (1, 3), (2, 1)), FCFS())), [5, 8, 9])

    def test_sjf(self):
        self.assertEqual(finishes(simulate(P((0, 5), (1, 3), (2, 1)), SJF())), [5, 9, 6])

    def test_srtf_preempts(self):
        r = simulate(P((0, 8), (1, 4), (2, 2)), SRTF())
        self.assertEqual(finishes(r), [14, 7, 4])

    def test_rr(self):
        r = simulate(P((0, 5), (1, 3), (2, 1)), RoundRobin(2))
        self.assertEqual(finishes(r), [9, 8, 5])

    def test_hrrn(self):
        r = simulate(P((0, 3), (1, 6), (2, 4), (3, 5), (4, 2)), HRRN())
        self.assertEqual(finishes(r), [3, 9, 15, 20, 11])

    def test_idle_gap(self):
        r = simulate(P((0, 2), (10, 2)), FCFS())
        self.assertEqual(r.gantt, [(0, 2, 0), (2, 10, None), (10, 12, 1)])

    def test_1000_processes_all_policies(self):
        procs = generate_workload(1000, seed=1)
        for name, cls in POLICIES.items():
            r = simulate(procs, cls())
            self.assertTrue(all(p.finish is not None and p.remaining == 0
                                for p in r.processes), name)
            self.assertTrue(all(p.waiting >= 0 for p in r.processes), name)
            busy = sum(e - s for s, e, pid in r.gantt if pid is not None)
            self.assertEqual(busy, sum(p.burst for p in procs), name)


if __name__ == "__main__":
    unittest.main()
