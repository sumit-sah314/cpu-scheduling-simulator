# Benchmark Results

Workload: 1000 processes, Poisson arrivals (2 per ms), exponential service times (mean 1 ms), seed 3360.

## Aperiodic schedulers

| Metric | FCFS | SJF | SRTF | RR (q=2 ms) | HRRN | Priority + Aging | MLFQ |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Total completion time (ms) | 955 | 955 | 955 | 955 | 955 | 955 | 955 |
| Avg turnaround time (ms) | 287.82 | 88.95 | 88.91 | 271.77 | 107.27 | 286.76 | 271.31 |
| Avg waiting time (ms) | 286.86 | 88.00 | 87.95 | 270.81 | 106.32 | 285.80 | 270.35 |
| Avg response time (ms) | 286.86 | 88.00 | 87.95 | 243.99 | 106.32 | 285.80 | 243.08 |
| Max waiting time (ms) | 539.00 | 901.00 | 901.00 | 840.00 | 887.00 | 539.00 | 847.00 |
| CPU utilization (%) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| Throughput (processes/s) | 1047.12 | 1047.12 | 1047.12 | 1047.12 | 1047.12 | 1047.12 | 1047.12 |
| Avg ready queue length | 300.38 | 92.14 | 92.10 | 283.57 | 111.33 | 299.27 | 283.09 |

![Average waiting time by algorithm](avg_waiting_time.png)

## Round Robin quantum sweep

| Quantum (ms) | Avg waiting (ms) | Reduction vs. FCFS |
| :--- | ---: | ---: |
| 0.5 | 239.06 | 16.7% |
| 1 | 239.96 | 16.4% |
| 2 | 270.81 | 5.6% |
| 4 | 285.29 | 0.5% |
| 10 | 286.86 | 0.0% |

![Round Robin quantum sweep](rr_quantum_sweep.png)

## Validation

The time-stepped FIFO simulator reports an average waiting time of 286.863 ms; the event-driven FCFS scheduler reports 286.863 ms.

## Real-time schedulers

Tasks (period, execution): T1=(4, 1), T2=(6, 2), T3=(12, 3).
Utilization U = 0.8333; RM bound = 0.7798; EDF bound = 1.0000.

| Policy | Timeline (1 ms slots) | Deadline misses |
| :--- | :--- | :--- |
| Rate-Monotonic | T1 T2 T2 T3 T1 T3 T2 T2 T1 T3 Idle Idle | 0 |
| Earliest-Deadline-First | T1 T2 T2 T3 T1 T3 T3 T2 T2 T1 Idle Idle | 0 |
