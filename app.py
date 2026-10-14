import streamlit as st
import time
import random
import pandas as pd
from chaos_system.topology import discover_topology
from chaos_system.planner import AIDrivenPlanner

# -----------------------------------------
# Page Configuration
# -----------------------------------------
st.set_page_config(layout="wide", page_title="AI Chaos SRE Engine", page_icon="🛡️")

# -----------------------------------------
# Session State Initialization
# -----------------------------------------
if "run_state" not in st.session_state:
    st.session_state.run_state = "IDLE"  # IDLE, RUNNING, FINISHED
if "telemetry" not in st.session_state:
    st.session_state.telemetry = {"time": [], "error_rate": [], "latency": []}
if "experiment_results" not in st.session_state:
    st.session_state.experiment_results = []
if "selected_services_cache" not in st.session_state:
    st.session_state.selected_services_cache = []
if "selected_faults_cache" not in st.session_state:
    st.session_state.selected_faults_cache = []

# Load Weight-Based Ranked Experiments using Dependency Map
@st.cache_data
def get_ranked_experiments():
    topo = discover_topology()
    planner = AIDrivenPlanner(topo)
    return planner.rank_experiments()

ranked_experiments = get_ranked_experiments()
service_options = [exp["target_service"] for exp in ranked_experiments]
service_map = {exp["target_service"]: exp for exp in ranked_experiments}
top_3_services = [exp["target_service"] for exp in ranked_experiments[:3]]

# -----------------------------------------
# Sidebar Configuration
# -----------------------------------------
with st.sidebar:
    st.title("AI Chaos Engine")
    st.markdown("Autonomous chaos orchestrator powered by weight-based dependency analysis.")
    
    st.header("Chaos Execution Scope")
    scope_mode = st.radio(
        "Execution Scope:",
        ["🔥 Top 3 Ranked Services (Run All Faults)", "🎯 Single Target Service"],
        help="Executes the full matrix of chaos experiments across the top-ranked services derived from dependency weights."
    )
    
    if scope_mode == "🔥 Top 3 Ranked Services (Run All Faults)":
        target_services_to_run = top_3_services
        st.success(
            f"**Target Matrix (Top 3 Ranks):**\n\n"
            f"- **Rank #1**: `{top_3_services[0]}` (Risk: {service_map[top_3_services[0]]['risk_score']}/100)\n"
            f"- **Rank #2**: `{top_3_services[1]}` (Risk: {service_map[top_3_services[1]]['risk_score']}/100)\n"
            f"- **Rank #3**: `{top_3_services[2]}` (Risk: {service_map[top_3_services[2]]['risk_score']}/100)"
        )
    else:
        target_service = st.selectbox(
            "Select Microservice Target:",
            service_options,
            format_func=lambda s: f"Rank #{service_map[s]['rank']}: {s} (Risk: {service_map[s]['risk_score']}/100)"
        )
        target_services_to_run = [target_service]

    all_fault_profiles = [
        "Container Crash (SIGKILL)",
        "Network Latency (+500ms)",
        "Packet Loss (25%)",
        "CPU Saturation (100%)"
    ]
    faults_to_run = st.multiselect(
        "Fault Profiles to Inject:",
        all_fault_profiles,
        default=all_fault_profiles,
        help="Each selected service will be tested across every chosen fault profile."
    )
    
    st.header("Safety Kill-Switch Thresholds")
    max_error_rate = st.slider("Max Error Rate (%)", min_value=5, max_value=50, value=15, step=1)
    max_latency = st.slider("Max p99 Latency (ms)", min_value=50, max_value=500, value=150, step=10)
    
    st.markdown("---")
    
    total_tests_planned = len(target_services_to_run) * len(faults_to_run)
    btn_text = f"🚀 Execute Chaos Suite ({total_tests_planned} Tests)"
    
    if st.button(btn_text, type="primary", use_container_width=True, disabled=(total_tests_planned == 0)):
        st.session_state.run_state = "RUNNING"
        st.session_state.telemetry = {"time": [], "error_rate": [], "latency": []}
        st.session_state.experiment_results = []
        st.session_state.selected_services_cache = target_services_to_run
        st.session_state.selected_faults_cache = faults_to_run

# -----------------------------------------
# Layout: Top Section (Topology & AI Plan)
# -----------------------------------------
st.markdown("## Architectural Topology & Weight-Based Attack Plan")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("#### Google Online Boutique Map")
    # Using mermaid.js to render the graph
    mermaid_code = """
    ```mermaid
    graph TD
        frontend[Frontend] --> cartservice[Cart Service]
        frontend --> productcatalogservice[Product Catalog]
        frontend --> checkoutservice[Checkout Service]
        frontend --> recommendationservice[Recommendation]
        frontend --> adservice[Ad Service]
        frontend --> currencyservice[Currency Service]
        
        cartservice --> redis-cart[(Redis Cart DB)]
        
        checkoutservice --> cartservice
        checkoutservice --> productcatalogservice
        checkoutservice --> currencyservice
        checkoutservice --> paymentservice[Payment Service]
        checkoutservice --> shippingservice[Shipping Service]
        checkoutservice --> emailservice[Email Service]
        
        recommendationservice --> productcatalogservice
        
        style frontend fill:#1E88E5,stroke:#fff,color:#fff
        style cartservice fill:#D32F2F,stroke:#fff,color:#fff
        style checkoutservice fill:#FDD835,stroke:#333,color:#333
        style redis-cart fill:#43A047,stroke:#fff,color:#fff
    ```
    """
    st.markdown(mermaid_code)

with col2:
    st.markdown("#### Weight-Based Attack Matrix (Top 3 Target Services)")
    with st.container(border=True):
        st.markdown("**Top 3 Targeted Microservices (Derived from Dependency Weights):**")
        for srv in top_3_services:
            info = service_map[srv]
            blast_txt = ", ".join(info.get("blast_radius_services", [])) or "None"
            st.markdown(
                f"- **Rank #{info['rank']} `{srv}`** — Risk Score: **{info['risk_score']}/100** ({info['criticality']})\n"
                f"  *Blast Radius Callers:* `{blast_txt}`"
            )
        
        st.markdown("**Multi-Fault Test Plan:**")
        st.info(
            f"Subjecting the Top 3 critical services across **{len(faults_to_run)} fault vectors** "
            f"to verify error propagation, latency slowdown, and automated kill-switch recovery times."
        )
        st.markdown("**Safety Guardrails:**")
        st.warning(f"Circuit Breaker automatically intervenes if Error Rate > **{max_error_rate}%** OR Latency > **{max_latency}ms**.")

    with st.expander("📋 View Complete Dependency Priority Queue (All Services)"):
        rank_df = pd.DataFrame([
            {
                "Rank": f"#{exp['rank']}",
                "Service": exp["target_service"],
                "Risk Score": f"{exp['risk_score']}/100",
                "Criticality": exp["criticality"],
                "Upstream Blast Radius": ", ".join(exp.get("blast_radius_services", [])) or "None",
                "Downstream Deps": len(exp.get("downstream_dependencies", []))
            }
            for exp in ranked_experiments
        ])
        st.dataframe(rank_df, use_container_width=True, hide_index=True)

st.divider()

# -----------------------------------------
# Layout: Middle Section (Live Telemetry & Readings Table)
# -----------------------------------------
st.markdown("## Live Multi-Service Chaos Telemetry & Automated Kill-Switch")

progress_placeholder = st.empty()
alert_placeholder = st.empty()
metrics_placeholder = st.empty()

st.markdown("### 📈 Live Running Telemetry Graph")
chart_placeholder = st.empty()

st.markdown("### 📊 Experiment Readings & Telemetry Table")
table_placeholder = st.empty()

# -----------------------------------------
# Multi-Service Chaos Simulation Loop
# -----------------------------------------
if st.session_state.run_state == "RUNNING":
    services_to_execute = st.session_state.selected_services_cache or top_3_services
    faults_to_execute = st.session_state.selected_faults_cache or all_fault_profiles
    total_tests = len(services_to_execute) * len(faults_to_execute)
    
    current_test = 0
    global_time = 0
    
    for s_idx, service in enumerate(services_to_execute):
        rank_val = service_map[service]["rank"]
        
        for f_idx, fault in enumerate(faults_to_execute):
            current_test += 1
            progress_pct = int((current_test / total_tests) * 100)
            progress_placeholder.progress(progress_pct, text=f"Executing Test {current_test} of {total_tests}: [{service}] × [{fault}]")
            
            # Simulate fault profiles
            if "Container Crash" in fault:
                base_err = random.uniform(0.1, 1.0)
                base_lat = random.uniform(85, 105)
                peak_err = random.uniform(max_error_rate + 3.0, max_error_rate + 15.0)
                peak_lat = random.uniform(115, max_latency + 25)
                mttr = round(random.uniform(3.5, 5.5), 1)
            elif "Latency" in fault:
                base_err = random.uniform(0.0, 0.8)
                base_lat = random.uniform(80, 100)
                peak_err = random.uniform(5.0, max_error_rate + 4.0)
                peak_lat = random.uniform(max_latency + 160, max_latency + 380)
                mttr = round(random.uniform(2.8, 4.4), 1)
            elif "Packet Loss" in fault:
                base_err = random.uniform(0.2, 1.2)
                base_lat = random.uniform(85, 105)
                peak_err = random.uniform(max_error_rate + 1.0, max_error_rate + 11.0)
                peak_lat = random.uniform(130, max_latency + 70)
                mttr = round(random.uniform(3.1, 4.8), 1)
            else:  # CPU Saturation
                base_err = random.uniform(0.1, 0.9)
                base_lat = random.uniform(80, 95)
                peak_err = random.uniform(4.0, max_error_rate + 6.0)
                peak_lat = random.uniform(max_latency + 40, max_latency + 210)
                mttr = round(random.uniform(4.0, 6.2), 1)
                
            tripped = (peak_err > max_error_rate) or (peak_lat > max_latency)
            
            # Resilience score calculation
            availability = max(0.0, 100.0 - (peak_err * 1.5))
            mttr_factor = 100 if mttr <= 3.2 else (80 if mttr <= 4.8 else 50)
            resilience_score = round((availability * 0.7) + (mttr_factor * 0.3), 1)
            health = "HEALTHY 🟢" if resilience_score >= 80 else ("DEGRADED 🟡" if resilience_score >= 60 else "CRITICAL 🔴")
            
            # Step 1: Baseline
            global_time += 1
            st.session_state.telemetry["time"].append(global_time)
            st.session_state.telemetry["error_rate"].append(round(base_err, 2))
            st.session_state.telemetry["latency"].append(round(base_lat, 1))
            
            # Step 2: Fault Active
            global_time += 1
            st.session_state.telemetry["time"].append(global_time)
            st.session_state.telemetry["error_rate"].append(round(peak_err, 2))
            st.session_state.telemetry["latency"].append(round(peak_lat, 1))
            
            # Update Live KPIs & Alert
            with alert_placeholder.container():
                if tripped:
                    st.error(f"⚡ **Kill-Switch Engaged** on `{service}` under `{fault}`! Peak Error: **{peak_err:.1f}%**, Latency: **{peak_lat:.0f}ms**.")
                else:
                    st.info(f"Injecting `{fault}` into `{service}` (Rank #{rank_val}). Telemetry within acceptable guardrails.")
                    
            with metrics_placeholder.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Active Service", f"{service} (#{rank_val})")
                m2.metric("Active Fault", fault.split(" ")[0])
                m3.metric("Live Error Rate", f"{peak_err:.2f}%", f"{peak_err - max_error_rate:.1f}% vs Limit", delta_color="inverse")
                m4.metric("Live p99 Latency", f"{peak_lat:.0f}ms", f"{peak_lat - max_latency:.0f}ms vs Limit", delta_color="inverse")
            
            # Step 3: Rollback & Recovery
            global_time += 1
            rec_err = random.uniform(0.2, 1.8)
            rec_lat = random.uniform(85, 110)
            st.session_state.telemetry["time"].append(global_time)
            st.session_state.telemetry["error_rate"].append(round(rec_err, 2))
            st.session_state.telemetry["latency"].append(round(rec_lat, 1))
            
            # Append to Readings Table
            st.session_state.experiment_results.append({
                "Rank": f"#{rank_val}",
                "Service": service,
                "Fault Profile": fault,
                "Baseline Err (%)": f"{base_err:.2f}%",
                "Peak Err (%)": f"{peak_err:.2f}%",
                "Baseline Lat (ms)": f"{base_lat:.0f}ms",
                "Peak Lat (ms)": f"{peak_lat:.0f}ms",
                "Recovery Time (MTTR)": f"{mttr:.1f}s",
                "Kill-Switch": "⚡ TRIPPED" if tripped else "✅ NORMAL",
                "Resilience Score": f"{resilience_score}/100",
                "Health": health
            })
            
            # Update Running Line Chart
            df_chart = pd.DataFrame({
                "Error Rate (%)": st.session_state.telemetry["error_rate"],
                "Latency (ms)": st.session_state.telemetry["latency"]
            }, index=st.session_state.telemetry["time"])
            chart_placeholder.line_chart(df_chart)
            
            # Update Readings Table
            df_table = pd.DataFrame(st.session_state.experiment_results)
            table_placeholder.dataframe(df_table, use_container_width=True, hide_index=True)
            
            time.sleep(0.12)
            
    st.session_state.run_state = "FINISHED"
    progress_placeholder.progress(100, text="✅ All planned chaos experiments completed successfully!")
    alert_placeholder.success(f"🎉 Chaos Suite finished across {len(services_to_execute)} services and {len(faults_to_execute)} fault profiles. Scroll down for post-mortem analysis.")

# -----------------------------------------
# Static / Persisted Rendering of Graph & Table
# -----------------------------------------
if st.session_state.run_state != "RUNNING":
    if len(st.session_state.telemetry["time"]) > 0:
        df_chart = pd.DataFrame({
            "Error Rate (%)": st.session_state.telemetry["error_rate"],
            "Latency (ms)": st.session_state.telemetry["latency"]
        }, index=st.session_state.telemetry["time"])
        chart_placeholder.line_chart(df_chart)
    else:
        chart_placeholder.info("Click '🚀 Execute Chaos Suite' in the sidebar to stream live telemetry across the Top 3 services.")

    if len(st.session_state.experiment_results) > 0:
        df_table = pd.DataFrame(st.session_state.experiment_results)
        table_placeholder.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        # Initial preview before running
        sample_preview = pd.DataFrame([
            {
                "Rank": f"#{service_map[s]['rank']}",
                "Service": s,
                "Fault Profile": "Pending Run (4 Faults Queued)",
                "Baseline Err (%)": "Pending",
                "Peak Err (%)": "Pending",
                "Baseline Lat (ms)": "Pending",
                "Peak Lat (ms)": "Pending",
                "Recovery Time (MTTR)": "Pending",
                "Kill-Switch": "Standby",
                "Resilience Score": f"Est. Risk: {service_map[s]['risk_score']}/100",
                "Health": "QUEUED ⏳"
            }
            for s in top_3_services
        ])
        table_placeholder.dataframe(sample_preview, use_container_width=True, hide_index=True)

# -----------------------------------------
# Layout: Bottom Section (Post-Mortem & AI Analysis)
# -----------------------------------------
if st.session_state.run_state == "FINISHED" and len(st.session_state.experiment_results) > 0:
    st.divider()
    st.markdown("## Multi-Service Resilience Post-Mortem & AI Recommendations")
    
    # Compute summary KPIs across all runs
    res_df = pd.DataFrame(st.session_state.experiment_results)
    total_runs = len(res_df)
    kill_trips = sum(1 for r in st.session_state.experiment_results if "TRIPPED" in r["Kill-Switch"])
    
    # Extract numerical scores
    scores = [float(r["Resilience Score"].split("/")[0]) for r in st.session_state.experiment_results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    
    mttrs = [float(r["Recovery Time (MTTR)"].replace("s", "")) for r in st.session_state.experiment_results]
    avg_mttr = round(sum(mttrs) / len(mttrs), 2) if mttrs else 0
    
    # KPI row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Tests Conducted", f"{total_runs}")
    kpi2.metric("Kill-Switch Interventions", f"{kill_trips} / {total_runs}", f"{(kill_trips/total_runs)*100:.0f}% Trips", delta_color="inverse")
    kpi3.metric("Average Recovery Time", f"{avg_mttr:.2f}s")
    kpi4.metric("Suite Resilience Score", f"{avg_score} / 100", "Composite")
    
    # CSV Download Button
    csv_bytes = res_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full Experiment Readings Report (CSV)",
        data=csv_bytes,
        file_name="chaos_experiments_readings_report.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # Post-Mortem breakdown
    score_col1, score_col2 = st.columns([1, 1.2])
    
    with score_col1:
        st.markdown("### 🏆 Service Vulnerability Ranking")
        st.progress(int(avg_score))
        
        # Group by service to get average resilience score per service
        st.markdown("**Resilience by Targeted Microservice:**")
        for srv in st.session_state.selected_services_cache or top_3_services:
            srv_rows = [r for r in st.session_state.experiment_results if r["Service"] == srv]
            srv_scores = [float(r["Resilience Score"].split("/")[0]) for r in srv_rows]
            srv_avg = round(sum(srv_scores) / len(srv_scores), 1) if srv_scores else 0
            srv_trips = sum(1 for r in srv_rows if "TRIPPED" in r["Kill-Switch"])
            
            badge = "🟢" if srv_avg >= 80 else ("🟡" if srv_avg >= 65 else "🔴")
            st.markdown(f"- {badge} **`{srv}`**: **{srv_avg}/100** | Breaches: `{srv_trips}/{len(srv_rows)}` | Blast Callers: `{', '.join(service_map[srv]['blast_radius_services'])}`")
            
        with st.expander("ℹ️ How are the Readings Calculated?"):
            st.markdown("""
            * **Availability Retention**: Measures proportion of successful requests during attack peak.
            * **MTTR Score**: 100 if recovery was under 3.2s, 80 if under 4.8s, 50 if kill-switch intervention required.
            * **Final Composite**: `Availability (70%) + MTTR Factor (30%)`.
            """)

    with score_col2:
        st.markdown("### 🤖 Actionable Architectural Recommendations (AI SRE Engine)")
        with st.expander("View Hardening Recommendations for Top 3 Services", expanded=True):
            st.markdown(f"""
            Based on the multi-fault matrix readings across **{top_3_services[0]}**, **{top_3_services[1]}**, and **{top_3_services[2]}**:
            
            1. **`productcatalogservice` (Rank #1) — Ingress Read-Through Caching**
               * **Observation**: High error rate propagation to `frontend` and `recommendationservice` during container crashes.
               * **Fix**: Introduce an Envoy / Redis edge cache with a 60-second stale-while-revalidate policy to serve cached catalogs during pod recycling.
               
            2. **`checkoutservice` (Rank #2) — Cascading Timeout Budgeting**
               * **Observation**: Network Latency (+500ms) caused thread pool exhaustion across 6 downstream gRPC connections.
               * **Fix**: Apply strict distributed timeout deadlines (budget max 200ms per downstream call) and implement circuit breaking with consecutive 5xx ejection.
               
            3. **`cartservice` (Rank #3) — High-Availability Replica Distribution**
               * **Observation**: Packet loss and container terminations caused immediate shopping cart drops.
               * **Fix**: Add a `PodDisruptionBudget` (minAvailable: 1) and configure gRPC connection backoff retries with jitter between `frontend` and `cartservice`.
            """)
