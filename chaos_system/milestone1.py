import time
import logging
import json
import os
import sys

from topology import discover_topology
from load_harness import LoadHarness
from chaos_engine import ChaosEngine
from planner import AIDrivenPlanner
from scoring import ResilienceAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Milestone1")

def main():
    # Setup paths - expecting to be run from Bosch-Hackathon root or chaos_system dir
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(base_dir, "microservices-demo", "release", "kubernetes-manifests.yaml")
    
    if not os.path.exists(manifest_path):
        logger.warning(f"Manifest not found at {manifest_path}. Using standard Google Online Boutique topology graph.")
        manifest_path = None

    logger.info("=== STEP 1: Topology Discovery ===")
    graph = discover_topology(manifest_path)
    logger.info(f"Discovered {len(graph)} services in topology map.")
    
    logger.info("=== STEP 2: Establish Baseline Load ===")
    # Note: Assumes frontend is port-forwarded to localhost:8080 or available there
    target_url = os.environ.get("FRONTEND_URL", "http://localhost:8080")
    logger.info(f"Starting load harness targeting {target_url}...")
    
    harness = LoadHarness(target_url)
    harness.start(concurrency=3)
    
    # Warmup and baseline collection
    logger.info("Warming up for 10 seconds to establish baseline...")
    time.sleep(10)
    baseline_metrics = harness.get_metrics()
    logger.info(f"Baseline Metrics: {baseline_metrics}")
    
    logger.info("=== STEP 3: AI Topology Ranking & Experiment Selection ===")
    planner = AIDrivenPlanner(graph)
    ranked_experiments = planner.rank_experiments()
    logger.info(f"AI discovered and ranked {len(ranked_experiments)} candidate experiments using dependency map:")
    for exp in ranked_experiments:
        logger.info(f"  [Rank {exp['rank']}] {exp['target_service']} (Risk Score: {exp['risk_score']}/100, Tier: {exp['criticality']}) | Blast Radius: {exp.get('blast_radius_services', [])}")
        logger.info(f"        Topological Rationale: {exp.get('ranking_rationale', '')}")

    # Select target: supports optional TARGET_SERVICE env override, defaults to AI Rank 1
    target_override = os.environ.get("TARGET_SERVICE")
    if target_override:
        plan = planner.select_experiment(target_override)
        logger.info(f"Selected target via TARGET_SERVICE override: {target_override} (Rank {plan.get('rank', 'N/A')})")
    else:
        plan = planner.select_top_experiment()
        logger.info(f"AI Automatically Selected Top-Ranked Target: {plan['target_service']} (Rank 1, Risk: {plan['risk_score']}/100)")

    logger.info(f"Selected Experiment Plan: {json.dumps(plan, indent=2)}")

    logger.info("=== STEP 4: Chaos Injection Engine with Kill-Switch ===")
    engine = ChaosEngine(harness)
    
    # This will block and run the experiment, triggering kill switch if needed
    engine.inject_container_kill(
        service_name=plan["target_service"],
        duration_seconds=plan["duration_seconds"],
        error_threshold=plan["safety_abort_criteria"]["max_error_rate"],
        latency_multiplier=plan["safety_abort_criteria"]["max_latency_multiplier"]
    )
    
    fault_metrics = harness.get_metrics()
    logger.info(f"Fault Metrics: {fault_metrics}")
    
    logger.info("Stopping load harness...")
    harness.stop()
    
    logger.info("=== STEP 5: Resilience Analysis & Scoring ===")
    analyzer = ResilienceAnalyzer(baseline_metrics, fault_metrics)
    report = analyzer.generate_report(plan)
    
    report_path = "executive_post_mortem.md"
    with open(report_path, "w") as f:
        f.write(report)
    logger.info(f"Generated Executive Post-Mortem at {report_path}")
    print("\n" + report)

    logger.info("=== STEP 6: AI-Driven Recommendations ===")
    logger.info("Consulting Gemini for fixes...")
    recs = analyzer.generate_ai_recommendations(report)
    
    recs_path = "ai_recommendations.md"
    with open(recs_path, "w") as f:
        f.write(recs)
    logger.info(f"Generated AI Recommendations at {recs_path}")
    print("\n" + recs)

if __name__ == "__main__":
    main()
