import argparse

from .simulator import POLICIES, RoundRobin, generate_workload, simulate


def main():
    ap = argparse.ArgumentParser(description="CPU scheduling simulator")
    ap.add_argument("-n", type=int, default=1000, help="number of processes")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quantum", type=int, default=4)
    ap.add_argument("--policies", nargs="+", default=list(POLICIES), choices=list(POLICIES))
    a = ap.parse_args()
    procs = generate_workload(a.n, a.seed)
    print(f"{'policy':9}{'avg_wait':>10}{'avg_tat':>10}{'avg_resp':>10}{'util':>7}{'ctx_sw':>8}")
    for name in a.policies:
        pol = RoundRobin(a.quantum) if name == "rr" else POLICIES[name]()
        r = simulate(procs, pol)
        print(f"{r.policy:9}{r.avg_waiting:10.2f}{r.avg_turnaround:10.2f}"
              f"{r.avg_response:10.2f}{r.cpu_utilization:7.2f}{r.context_switches:8d}")


main()
