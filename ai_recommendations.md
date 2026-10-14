## AI Recommendations for Fixes

Based on the experiment data—specifically the ~21% error rate spike and the low MTTR factor during a single `container_kill` fault—the system demonstrates vulnerability to transient pod loss and lack of graceful degradation on upstream dependencies. 

Here are four concrete engineering recommendations to harden the architecture:

---

### 1. Implement High Availability Deployment with PodDisruptionBudgets
The 20.74% error rate strongly indicates that `cartservice` was either running as a single replica or lacked proper distribution across nodes to absorb instantaneous termination.
* **Action**:
  * Set `spec.replicas` to a minimum of **2** (ideally 3) across distinct availability zones using `topologySpreadConstraints` or `podAntiAffinity`.
  * Define a `PodDisruptionBudget` (PDB) to ensure at least one instance remains available during voluntary/involuntary evictions:
    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: cartservice-pdb
    spec:
      minAvailable: 1
      selector:
        matchLabels:
          app: cartservice
    ```
* **Target Impact**: Prevents 100% loss of the cart backend when a single container crashes, immediately reducing the error rate during pod recycling.

---

### 2. Configure Circuit Breaking and Graceful Fallback in the Frontend
The hypothesis stipulated that product browsing and catalog operations should remain unaffected with graceful messaging; however, cascading errors still propagated to users.
* **Action**:
  * Implement an active **Circuit Breaker** (via Istio `DestinationRule`, Envoy, or client-side libraries) on calls from the frontend to `cartservice`.
  * Configure consecutive error trip conditions (e.g., trip after 3 consecutive failures within 5 seconds, open for 10 seconds).
  * Implement an application-level UI fallback: when the circuit is open or cart calls return `UNAVAILABLE` (gRPC status 14), render the catalog pages with a degraded banner (*"Cart is temporarily unavailable, browsing remains active"*) instead of failing the request with HTTP 500.
* **Target Impact**: Isolates cart failures entirely from the browsing and discovery paths, protecting availability retention above 95%.

---

### 3. Tune Health Probes and Container Lifecycle to Minimize MTTR
The MTTR Factor (50) indicates that Kubernetes traffic routing took too long to stop directing requests to the dead pod and too long to recognize the replacement pod as healthy.
* **Action**:
  * Add a `preStop` hook to give the network layer time to update endpoints before the SIGTERM kills the process:
    ```yaml
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]
    ```
  * Optimize `readinessProbe` and `startupProbe` on `cartservice`:
    * Set `periodSeconds: 2` and `failureThreshold: 1` on the readiness probe so kube-proxy and Ingress immediately drain traffic upon failure.
    * Use a dedicated `startupProbe` to accelerate the cold-start recognition of the replacement container without causing premature liveness failures.
* **Target Impact**: Significantly reduces the MTTR factor and eliminates the transient window where requests are sent to a terminated container.

---

### 4. Implement Smart gRPC Retries with Backoff and Request Hedging
Calls dropped during container kill were likely unhandled RPC disconnections that failed fast to the client.
* **Action**:
  * Configure gRPC/HTTP retry policies in the frontend client configuration or Service Mesh:
    * **Retry On**: `UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `503 Service Unavailable`.
    * **Max Attempts**: 2–3 retries with exponential backoff and jitter (initial interval: 25ms, max interval: 100ms).
    * **Timeouts**: Enforce a strict upstream timeout of `200ms` for cart operations to avoid inflating p99 latencies during retry cascades.
* **Target Impact**: Masks instantaneous pod restarts from end-users, absorbing the transient downtime within acceptable p99 latency thresholds (under 150ms).