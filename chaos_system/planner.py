import json
import os
import logging
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
logger = logging.getLogger("AIDrivenPlanner")

class AIDrivenPlanner:
    def __init__(self, topology_graph):
        self.topology = topology_graph or {}
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = 'gemini-3.8-flash'
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.client = None
        else:
            self.client = None

    def rank_experiments(self):
        """
        Analyzes the microservice dependency topology graph, scores blast radius and criticality,
        and returns a sorted list of candidate chaos experiments (Rank 1 being highest priority).
        """
        if self.client:
            ai_ranked = self._rank_with_gemini()
            if ai_ranked:
                return ai_ranked

        logger.info("Using topological dependency analyzer to rank chaos experiments.")
        return self._heuristic_ranked_plan()

    def _rank_with_gemini(self):
        prompt = f"""
You are an expert Cloud-Native SRE and Chaos Engineering AI.
I have the following microservice topology graph detailing dependencies and upstream dependents:
{json.dumps(self.topology, indent=2)}

Analyze the architectural dependency map considering:
1. Ingress path and upstream callers (blast radius / fan-in)
2. Downstream dependencies (orchestration depth / fan-out)
3. Transaction criticality (cart, checkout, payment paths)
4. Single points of failure (e.g. data stores like redis-cart)

Rank the candidate chaos experiments from highest priority/risk (Rank 1) to lower priorities.
Output ONLY a JSON array of objects (do not wrap in markdown or backticks):
[
  {{
    "rank": 1,
    "target_service": "cartservice",
    "risk_score": 95,
    "criticality": "CRITICAL",
    "blast_radius_services": ["frontend", "checkoutservice"],
    "fault_type": "container_kill",
    "fault_params": {{"replicas": 0}},
    "duration_seconds": 30,
    "hypothesis": "Terminating cartservice will degrade cart mutations and checkout flow. Frontend must display fallback states without total 500 error cascades.",
    "ranking_rationale": "High topological centrality on the core purchase funnel. Direct dependency for both frontend and checkoutservice.",
    "safety_abort_criteria": {{
      "max_error_rate": 0.15,
      "max_latency_multiplier": 3.0
    }}
  }}
]
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response.split("```json", 1)[1].strip()
            elif text_response.startswith("```"):
                text_response = text_response.split("```", 1)[1].strip()
            if text_response.endswith("```"):
                text_response = text_response.rsplit("```", 1)[0].strip()

            ranked = json.loads(text_response)
            if isinstance(ranked, list) and len(ranked) > 0:
                # Ensure rank index
                for idx, item in enumerate(ranked, 1):
                    item["rank"] = item.get("rank", idx)
                return ranked
        except Exception as e:
            logger.warning(f"Gemini experiment ranking failed ({e}). Falling back to graph-based ranking.")
        return None

    def _heuristic_ranked_plan(self):
        """
        Topological graph analyzer that computes centrality, in-degree (blast radius),
        out-degree, and architectural tier weights from the dependency graph.
        """
        tier_weights = {
            "cartservice": 95,
            "checkoutservice": 92,
            "paymentservice": 88,
            "redis-cart": 85,
            "productcatalogservice": 78,
            "recommendationservice": 65,
            "currencyservice": 60,
            "shippingservice": 60,
            "adservice": 50,
            "emailservice": 45,
        }

        rationales = {
            "cartservice": "Highest blast radius on the conversion path. Directly queried by frontend and checkoutservice, and acts as sole gateway to redis-cart state store.",
            "checkoutservice": "Orchestration nexus for all purchases. Fan-out to 6 downstream services; failure completely halts e-commerce order completion.",
            "paymentservice": "Critical financial transactional dependency. Checkout flow blocks synchronously on payment approval with zero fallback tolerance.",
            "redis-cart": "Single Point of Failure (SPOF) for shopping session state. Container crash wipes or blocks in-flight cart operations.",
            "productcatalogservice": "Core content discovery hub. Queried by frontend, checkoutservice, and recommendationservice.",
            "recommendationservice": "Browsing engagement dependency. Graceful degradation should allow browsing even if ML recommendations drop.",
            "shippingservice": "Fulfillment service needed for quote and order checkout calculations.",
            "currencyservice": "Localization service for international prices. Currency cache can mask transient dropouts.",
            "adservice": "Ancillary monetization service. Failure should be fully isolated without impacting core conversion funnel.",
            "emailservice": "Asynchronous notification consumer. Failure should be queued or isolated from checkout response time."
        }

        candidates = []
        for svc, meta in self.topology.items():
            if svc == "frontend":
                continue  # frontend is the ingress entrypoint, not the fault target

            dependents = meta.get("dependents", [])
            dependencies = meta.get("dependencies", [])
            base_w = tier_weights.get(svc, 50)
            
            # Topological risk score: combination of architectural tier + blast radius (dependents) + dependencies
            score = min(99, int(base_w * 0.55 + len(dependents) * 18 + len(dependencies) * 4))
            crit = "CRITICAL" if score >= 85 else ("HIGH" if score >= 70 else "MEDIUM")
            rationale = rationales.get(svc, f"Node with {len(dependents)} upstream callers and {len(dependencies)} downstream dependencies.")

            candidates.append({
                "target_service": svc,
                "risk_score": score,
                "criticality": crit,
                "blast_radius_services": dependents,
                "downstream_dependencies": dependencies,
                "fault_type": "container_kill",
                "fault_params": {"replicas": 0},
                "duration_seconds": 30,
                "hypothesis": f"Verify whether upstream services gracefully isolate a {svc} outage or suffer cascading failure.",
                "ranking_rationale": rationale,
                "safety_abort_criteria": {
                    "max_error_rate": 0.15,
                    "max_latency_multiplier": 3.0
                }
            })

        # Sort descending by risk score
        candidates.sort(key=lambda x: x["risk_score"], reverse=True)
        for idx, item in enumerate(candidates, 1):
            item["rank"] = idx

        return candidates

    def select_top_experiment(self):
        """Returns the highest ranked candidate experiment."""
        ranked = self.rank_experiments()
        if ranked:
            top = ranked[0]
            top["ranked_candidates"] = ranked
            return top
        return self._heuristic_fallback_single()

    def select_experiment(self, target_service: str):
        """Returns the experiment plan for a specific service target from the ranked pool."""
        ranked = self.rank_experiments()
        for exp in ranked:
            if exp["target_service"] == target_service:
                exp["ranked_candidates"] = ranked
                return exp
        
        # If not found in ranking, build fallback
        plan = self._heuristic_fallback_single()
        plan["target_service"] = target_service
        plan["ranked_candidates"] = ranked
        return plan

    def generate_experiment_plan(self):
        """
        Backwards-compatible interface for milestone1:
        Ranks all experiments using the dependency map and selects the top-ranked experiment.
        """
        return self.select_top_experiment()

    def _heuristic_fallback_single(self):
        return {
            "rank": 1,
            "target_service": "cartservice",
            "risk_score": 92,
            "criticality": "CRITICAL",
            "blast_radius_services": ["frontend", "checkoutservice"],
            "fault_type": "container_kill",
            "fault_params": {"replicas": 0},
            "duration_seconds": 30,
            "hypothesis": "Verify whether frontend degrades gracefully if cartservice is unavailable.",
            "ranking_rationale": "High blast radius across frontend and checkout paths.",
            "safety_abort_criteria": {
                "max_error_rate": 0.15,
                "max_latency_multiplier": 3.0
            }
        }
