import subprocess
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosEngine")

class ChaosEngine:
    def __init__(self, load_harness):
        self.load_harness = load_harness
        self.execution_history = []
        
    def inject_container_kill(self, service_name, duration_seconds=30, error_threshold=0.15, latency_multiplier=3.0):
        # 1. Capture baseline metrics
        baseline = self.load_harness.get_metrics()
        baseline_p99 = baseline["p99"] or 0.1 # default 100ms if empty
        logger.info(f"Baseline p99 latency: {baseline_p99:.4f}s")
        
        # 2. Inject fault
        logger.info(f"Injecting fault: Scaling down {service_name} to 0 replicas...")
        self._scale_deployment(service_name, 0)
        
        # 3. Monitor with Blast Radius Safety Circuit Breaker
        end_time = time.time() + duration_seconds
        triggered_safety = False
        
        try:
            while time.time() < end_time:
                time.sleep(2)
                metrics = self.load_harness.get_metrics()
                error_rate = metrics["error_rate"]
                p99 = metrics["p99"]
                
                logger.info(f"Monitoring | Error Rate: {error_rate:.2%} | p99: {p99:.4f}s")
                
                if error_rate > error_threshold:
                    logger.warning(f"SAFETY BREACH: Error rate {error_rate:.2%} > {error_threshold:.2%}")
                    triggered_safety = True
                    break
                    
                if p99 > (baseline_p99 * latency_multiplier):
                    logger.warning(f"SAFETY BREACH: p99 latency {p99:.4f}s > {baseline_p99 * latency_multiplier:.4f}s")
                    triggered_safety = True
                    break
        finally:
            # 4. Rollback / Kill Switch
            logger.info(f"Reverting fault: Scaling {service_name} back to 1 replica...")
            self._scale_deployment(service_name, 1)
            
            if triggered_safety:
                logger.error("Experiment aborted by safety circuit breaker.")
            else:
                logger.info("Experiment completed normally.")
                
            self._write_execution_log()

    def _scale_deployment(self, service_name, replicas):
        cmd = ["kubectl", "scale", "deployment", service_name, f"--replicas={replicas}"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        log_entry = {
            "timestamp": timestamp,
            "command": " ".join(cmd),
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
        self.execution_history.append(log_entry)
        
        if result.returncode != 0:
            logger.error(f"Failed to scale {service_name}: Exit {result.returncode} - {result.stderr}")

    def _write_execution_log(self):
        log_path = "execution_log.md"
        with open(log_path, "w") as f:
            f.write("# Chaos Engine Execution Log\n\n")
            f.write("This file contains the precise execution history, timestamps, exit codes, and error logs for the underlying system commands run during the experiment.\n\n")
            
            for idx, entry in enumerate(self.execution_history, 1):
                f.write(f"### Action {idx}: `{entry['command']}`\n")
                f.write(f"- **Timestamp**: {entry['timestamp']}\n")
                f.write(f"- **Exit Code**: `{entry['exit_code']}`\n")
                
                if entry['stdout']:
                    f.write(f"**Stdout**:\n```text\n{entry['stdout']}\n```\n")
                    
                if entry['stderr']:
                    f.write(f"**Stderr/Error Log**:\n```text\n{entry['stderr']}\n```\n")
                
                f.write("---\n")
                
        logger.info(f"Generated Execution Log at {log_path}")
