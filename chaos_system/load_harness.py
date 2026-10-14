import requests
import threading
import time
import statistics

class LoadHarness:
    def __init__(self, target_url="http://localhost:8080"):
        self.target_url = target_url
        self.running = False
        self.latencies = []
        self.errors = 0
        self.total_requests = 0
        self.lock = threading.Lock()
        
    def worker(self):
        while self.running:
            start_time = time.time()
            try:
                response = requests.get(self.target_url, timeout=2.0)
                latency = time.time() - start_time
                with self.lock:
                    self.total_requests += 1
                    self.latencies.append(latency)
                    if response.status_code >= 400:
                        self.errors += 1
            except requests.RequestException:
                with self.lock:
                    self.total_requests += 1
                    self.errors += 1
            
            time.sleep(0.1) # Simulate pacing

    def start(self, concurrency=5):
        self.running = True
        self.threads = []
        for _ in range(concurrency):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            self.threads.append(t)
            
    def stop(self):
        self.running = False
        for t in self.threads:
            t.join()
            
    def get_metrics(self):
        with self.lock:
            if not self.latencies:
                return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "error_rate": 0.0, "total": self.total_requests}
                
            sorted_lat = sorted(self.latencies)
            p50 = statistics.quantiles(sorted_lat, n=100)[49] if len(sorted_lat) > 100 else sorted_lat[len(sorted_lat)//2]
            p95 = statistics.quantiles(sorted_lat, n=100)[94] if len(sorted_lat) > 100 else sorted_lat[int(len(sorted_lat)*0.95)]
            p99 = statistics.quantiles(sorted_lat, n=100)[98] if len(sorted_lat) > 100 else sorted_lat[int(len(sorted_lat)*0.99)]
            error_rate = (self.errors / self.total_requests) if self.total_requests > 0 else 0
            
            metrics = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "error_rate": error_rate,
                "total": self.total_requests,
                "errors": self.errors
            }
            
            # Reset rolling window
            self.latencies = self.latencies[-1000:]
            
            return metrics
