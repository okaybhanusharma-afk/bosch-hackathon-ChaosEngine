import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class ResilienceAnalyzer:
    def __init__(self, baseline_metrics, fault_metrics):
        self.baseline = baseline_metrics
        self.fault = fault_metrics
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = 'gemini-3.8-flash'
        else:
            self.client = None
        
    def generate_report(self, plan):
        availability_retention = max(0, 100 * (1.0 - self.fault["error_rate"]))
        
        # Simple heuristic MTTR score
        mttr_score = 100 if self.fault["error_rate"] <= plan["safety_abort_criteria"]["max_error_rate"] else 50
        
        score = (availability_retention * 0.7) + (mttr_score * 0.3)
        
        if score > 90:
            system_health = "HEALTHY"
        elif score >= 70:
            system_health = "DEGRADED"
        else:
            system_health = "CRITICAL"
            
        report = f"""# Executive Post-Mortem: Resilience Experiment

## Experiment Details
- **Target Service**: {plan['target_service']}
- **Fault Type**: {plan['fault_type']}
- **Hypothesis**: {plan['hypothesis']}

## Telemetry Comparison
| Metric | Baseline | During Fault |
|--------|----------|--------------|
| Error Rate | {self.baseline['error_rate']:.2%} | {self.fault['error_rate']:.2%} |
| Latency p99 | {self.baseline['p99']:.4f}s | {self.fault['p99']:.4f}s |

## System Resilience Score: {score:.1f}/100
- **System Health**: {system_health}
- Availability Retention: {availability_retention:.1f}%
- MTTR Factor: {mttr_score}
"""
        return report

    def generate_ai_recommendations(self, report_content):
        if not self.client:
            return "## AI Recommendations\n\n*Skipped: No GEMINI_API_KEY found in .env.*"
            
        prompt = f"""
You are an expert Cloud-Native SRE. I have just run a Chaos Engineering experiment on my Kubernetes microservices.
Below is the post-mortem report:

{report_content}

Please provide 3-5 concrete, actionable engineering recommendations to improve the resilience of this system. 
Format your output entirely in Markdown as a section starting with "## AI Recommendations for Fixes".
Do not include markdown codeblock tags like ```markdown.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text_response = response.text.strip()
            # Clean up potential markdown formatting
            if text_response.startswith("```markdown"):
                text_response = text_response.split("```markdown", 1)[1].strip()
            if text_response.endswith("```"):
                text_response = text_response.rsplit("```", 1)[0].strip()
            return text_response
        except Exception as e:
            return f"## AI Recommendations\n\n*Error generating recommendations: {e}*"
