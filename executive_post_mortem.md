# Executive Post-Mortem: Resilience Experiment

## Experiment Details
- **Target Service**: cartservice
- **Fault Type**: container_kill
- **Hypothesis**: Terminating cartservice will degrade cart mutations and checkout flows, but frontend product browsing and catalog operations will remain available with graceful fallback messages rather than unhandled cascading failures across the frontend.

## Telemetry Comparison
| Metric | Baseline | During Fault |
|--------|----------|--------------|
| Error Rate | 0.00% | 20.74% |
| Latency p99 | 0.0879s | 0.1056s |

## System Resilience Score: 70.5/100
- **System Health**: DEGRADED 🟡
- Availability Retention: 79.3%
- MTTR Factor: 50
