# AI-Driven Chaos Engineering for Cloud-Native Resilience

This system is designed to run autonomous chaos experiments on the Google Cloud Online Boutique microservices demo.

## Prerequisites
- Python 3.9+
- Local Kubernetes cluster (e.g., Minikube or kind)
- `kubectl` configured to access the cluster

## Setup and Boot

1. **Start Local Kubernetes Cluster**
   ```bash
   minikube start --cpus=4 --memory=8192
   ```

2. **Deploy the Online Boutique App**
   ```bash
   # From the repository root
   kubectl apply -f microservices-demo/release/kubernetes-manifests.yaml
   ```

3. **Wait for Pods to be Ready**
   ```bash
   kubectl wait --for=condition=available --timeout=300s deployment/frontend
   ```

4. **Port Forward the Frontend Service**
   ```bash
   kubectl port-forward deployment/frontend 8080:8080
   ```
   *(Keep this running in a separate terminal)*

5. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the AI-Driven Chaos Experiment (Milestone 1)**
   ```bash
   python chaos_system/milestone1.py
   ```

## Architecture Modules
1. **Topology & Dependency Discovery Engine** (`topology.py`): Parses Kubernetes manifests to discover services and their dependencies.
2. **Baseline Telemetry & Load Harness** (`load_harness.py`): Hits the frontend to establish a steady-state baseline and monitors latency and error rates.
3. **Chaos Injection Engine** (`chaos_engine.py`): Injects faults (e.g. killing containers via `kubectl scale`) with an automated blast-radius circuit breaker.
4. **AI-Driven Experiment Planner** (`planner.py`): Determines target services and experiment hypotheses based on topology mapping.
5. **Resilience Analysis & Scoring Engine** (`scoring.py`): Compares baseline and fault metrics to output a System Resilience Score and executive markdown report.
