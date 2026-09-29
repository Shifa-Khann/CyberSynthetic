"""
pages/6_Lineage.py
Incident Lineage Explorer — Trace security incidents end-to-end.
"""
import pathlib
import sys

import pandas as pd
import streamlit as st

from engine.ui_styles import inject_css, sidebar_nav

st.set_page_config(
    page_title="Incident Lineage · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Incident Lineage Explorer")
st.markdown(
    "Trace cybersecurity incidents end-to-end through the complete attack lifecycle: "
    "Incident → Alerts → Telemetry → Target User & Device → Threat IOCs → PDF Report."
)
st.divider()

result = st.session_state.get("last_result") or st.session_state.get("last_upload_result")
if not result or "tables" not in result:
    st.info("No active scenario dataset found in memory. Navigate to Generate Data and run a scenario first.")
    st.stop()

tables = result["tables"]

incidents_df = tables.get("incidents", pd.DataFrame())
alerts_df = tables.get("alerts", pd.DataFrame())
auth_df = tables.get("auth_events", pd.DataFrame())
process_df = tables.get("process_events", pd.DataFrame())
users_df = tables.get("users", pd.DataFrame())
devices_df = tables.get("devices", pd.DataFrame())
indicators_df = tables.get("indicators", pd.DataFrame())

if incidents_df.empty:
    st.warning("No security incidents found in the active dataset.")
    st.stop()

inc_ids = incidents_df["incident_id"].tolist()

c_sel, c_kpi = st.columns([2, 4], gap="large")

with c_sel:
    st.markdown("<div class='section-title'>Select Security Incident</div>", unsafe_allow_html=True)
    selected_id = st.selectbox("Active Incident ID", inc_ids, label_visibility="collapsed")

inc = incidents_df[incidents_df["incident_id"] == selected_id].iloc[0]

SEV_COLORS = {
    "critical": "#ef4444",
    "high": "#f97316",
    "medium": "#f59e0b",
    "low": "#10b981",
}
sev = str(inc.get("severity", "")).lower()
sev_color = SEV_COLORS.get(sev, "#9ca3af")

with c_kpi:
    st.markdown("<div class='section-title'>Incident Summary KPI</div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Severity", sev.upper())
    k2.metric("Status", str(inc.get("status", "OPEN")).upper())
    k3.metric("Target User", str(inc.get("victim_user_id", "N/A")))
    k4.metric("Target Asset", str(inc.get("primary_device_id", "N/A")))

st.divider()

# ── Incident Overview Header ──────────────────────────────────────────────────
st.markdown(
    f"""
<div style="background:#111827; border:1px solid #1f2937; border-left:4px solid {sev_color};
border-radius:8px; padding:1.25rem 1.5rem; margin-bottom:1.5rem;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
    <div style="font-size:1.1rem; font-weight:800; color:#f9fafb;">
        {selected_id} &mdash; <span style="color:{sev_color};">{sev.upper()} SEVERITY INCIDENT</span>
    </div>
    <span class="tag tag-purple">MITRE ATT&amp;CK: {inc.get('mitre_tactics','N/A')}</span>
  </div>
  <div style="display:flex; gap:2.5rem; flex-wrap:wrap; font-size:0.85rem; color:#d1d5db;">
    <span><strong>Start Time:</strong> {inc.get('start_time','N/A')}</span>
    <span><strong>End Time:</strong> {inc.get('end_time','N/A')}</span>
    <span><strong>Victim User:</strong> {inc.get('victim_user_id','N/A')}</span>
    <span><strong>Asset ID:</strong> {inc.get('primary_device_id','N/A')}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
t_flow, t_timeline, t_entities, t_iocs, t_report = st.tabs([
    "Attack Lineage Flow",
    "Chronological Event Timeline",
    "User & Asset Context",
    "Threat Indicators (IOCs)",
    "Incident PDF Report",
])

# ── TAB 1: Visual Attack Lineage Flow ─────────────────────────────────────────
with t_flow:
    st.markdown("### End-to-End Attack Progression")
    st.caption("Visual breakdown of how telemetry events triggered alerts and escalated into this security incident.")

    inc_alerts = alerts_df[alerts_df["incident_id"] == selected_id] if not alerts_df.empty else pd.DataFrame()
    event_ids = inc_alerts["source_event_id"].dropna().unique().tolist() if not inc_alerts.empty else []

    # Step Cards
    col_step1, col_step2, col_step3 = st.columns(3)

    with col_step1:
        with st.container(border=True):
            st.markdown("<span class='tag tag-blue'>Stage 1: Initial Telemetry</span>", unsafe_allow_html=True)
            st.markdown("#### Source Events")
            st.write(f"**Total Linked Events:** {len(event_ids)}")
            if event_ids:
                for eid in event_ids[:3]:
                    st.code(f"Event ID: {eid}")
            else:
                st.info("No raw telemetry events linked.")

    with col_step2:
        with st.container(border=True):
            st.markdown("<span class='tag tag-amber'>Stage 2: Detection Alerts</span>", unsafe_allow_html=True)
            st.markdown("#### Correlated Alerts")
            st.write(f"**Total Triggered Alerts:** {len(inc_alerts)}")
            if not inc_alerts.empty:
                for _, alt in inc_alerts.iterrows():
                    a_sev = str(alt.get("severity", "")).lower()
                    a_clr = SEV_COLORS.get(a_sev, "#9ca3af")
                    st.markdown(
                        f"• <strong style='color:{a_clr}'>[{a_sev.upper()}]</strong> "
                        f"{alt.get('alert_type','Alert')} (`{alt.get('alert_id','')}`)"
                    )
            else:
                st.info("No alerts found.")

    with col_step3:
        with st.container(border=True):
            st.markdown("<span class='tag tag-red'>Stage 3: Escalate Incident</span>", unsafe_allow_html=True)
            st.markdown("#### Incident Impact")
            st.write(f"**Incident ID:** `{selected_id}`")
            st.write(f"**Target User:** `{inc.get('victim_user_id','N/A')}`")
            st.write(f"**Target Asset:** `{inc.get('primary_device_id','N/A')}`")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Detailed Linked Alerts Table")
    if not inc_alerts.empty:
        st.dataframe(inc_alerts.astype(str), use_container_width=True)
        st.download_button(
            "Download Linked Alerts CSV",
            data=inc_alerts.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{selected_id}_alerts.csv",
            mime="text/csv",
        )

# ── TAB 2: Chronological Event Timeline ───────────────────────────────────────
with t_timeline:
    st.markdown("### Telemetry Event Sequence")

    events_list = []

    if not auth_df.empty and "event_id" in auth_df.columns and event_ids:
        matching_auth = auth_df[auth_df["event_id"].isin(event_ids)]
        for _, r in matching_auth.iterrows():
            events_list.append({
                "Timestamp": r.get("ts", "N/A"),
                "Type": "Auth Event",
                "User / Source": r.get("user_id", "N/A"),
                "Source IP": r.get("src_ip", "N/A"),
                "Outcome": r.get("outcome", "N/A"),
                "Label": str(r.get("label", "N/A")).upper(),
                "Details": f"City: {r.get('geo_city','N/A')} | Auth Method: {r.get('auth_method','N/A')}",
            })

    if not process_df.empty and "event_id" in process_df.columns and event_ids:
        matching_proc = process_df[process_df["event_id"].isin(event_ids)]
        for _, r in matching_proc.iterrows():
            events_list.append({
                "Timestamp": r.get("ts", "N/A"),
                "Type": "Process Event",
                "User / Source": r.get("user_id", "N/A"),
                "Source IP": r.get("device_id", "N/A"),
                "Outcome": r.get("process_name", "N/A"),
                "Label": str(r.get("label", "N/A")).upper(),
                "Details": f"Cmd: {r.get('command_line','')[:70]}",
            })

    if events_list:
        timeline_df = pd.DataFrame(events_list).sort_values("Timestamp")
        st.dataframe(timeline_df, use_container_width=True)

        for item in events_list:
            lbl_clr = "#10b981" if item["Label"] == "NORMAL" else "#ef4444"
            st.markdown(
                f"""
<div style="border-left: 3px solid {lbl_clr}; padding-left: 1rem; margin-bottom: 0.75rem;">
    <span style="font-size:0.8rem; color:#9ca3af;">{item['Timestamp']}</span> &mdash;
    <strong style="color:#f9fafb;">[{item['Type']}]</strong> {item['User / Source']} ({item['Source IP']})
    &nbsp;&middot;&nbsp; Label: <strong style="color:{lbl_clr};">{item['Label']}</strong><br>
    <span style="font-size:0.85rem; color:#d1d5db;">{item['Details']}</span>
</div>
""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No detailed telemetry records found for these event IDs.")

# ── TAB 3: User & Asset Context ───────────────────────────────────────────────
with t_entities:
    col_u, col_d = st.columns(2)

    with col_u:
        st.markdown("#### Target Victim User Profile")
        victim_id = inc.get("victim_user_id")
        if victim_id and not users_df.empty:
            u_row = users_df[users_df["user_id"] == victim_id]
            if not u_row.empty:
                u = u_row.iloc[0]
                with st.container(border=True):
                    st.markdown(f"### {u.get('full_name','User')} (`{victim_id}`)")
                    st.write(f"**Username:** `{u.get('username','')}`")
                    st.write(f"**Email Address:** `{u.get('email','')}`")
                    st.write(f"**Department:** {u.get('department','')}")
                    st.write(f"**Job Title:** {u.get('role','')}")
                    st.write(f"**Privilege Level:** `{u.get('privilege_level','')}`")
                    st.write(f"**Location:** {u.get('home_city','')}")
            else:
                st.info(f"User ID `{victim_id}` not found in users table.")
        else:
            st.info("No victim user associated.")

    with col_d:
        st.markdown("#### Primary Target Asset / Device")
        device_id = inc.get("primary_device_id")
        if device_id and not devices_df.empty:
            d_row = devices_df[devices_df["device_id"] == device_id]
            if not d_row.empty:
                d = d_row.iloc[0]
                with st.container(border=True):
                    st.markdown(f"### {d.get('hostname','Device')} (`{device_id}`)")
                    st.write(f"**Operating System:** {d.get('os','')}")
                    st.write(f"**IP Address:** `{d.get('ip_address','')}`")
                    st.write(f"**Criticality Rating:** `{str(d.get('criticality','')).upper()}`")
            else:
                st.info(f"Device ID `{device_id}` not found in devices table.")
        else:
            st.info("No primary asset associated.")

# ── TAB 4: Threat Indicators (IOCs) ───────────────────────────────────────────
with t_iocs:
    st.markdown("#### Threat Indicators of Compromise (IOCs)")
    if not indicators_df.empty:
        iocs = indicators_df[indicators_df["incident_id"] == selected_id]
        if not iocs.empty:
            display_cols = [c for c in ["indicator_id", "type", "value", "confidence"] if c in iocs.columns]
            st.dataframe(iocs[display_cols].astype(str), use_container_width=True)
            st.download_button(
                "Download Incident IOCs CSV",
                data=iocs[display_cols].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{selected_id}_iocs.csv",
                mime="text/csv",
            )
        else:
            st.info("No specific indicators of compromise associated with this incident.")
    else:
        st.info("No indicators table available in active dataset.")

# ── TAB 5: PDF Report Download ────────────────────────────────────────────────
with t_report:
    st.markdown("#### Download PDF Security Incident Report")
    if result.get("run_id"):
        out_dir = pathlib.Path("outputs") / result["run_id"] / "reports"
        if out_dir.exists():
            pdfs = list(out_dir.glob(f"{selected_id}*.pdf"))
            if pdfs:
                for pdf in pdfs:
                    with open(pdf, "rb") as f:
                        st.download_button(
                            f"Download PDF Report ({pdf.name})",
                            data=f.read(),
                            file_name=pdf.name,
                            mime="application/pdf",
                            key=f"pdf_lineage_{pdf.name}",
                        )
            else:
                st.info("No PDF report generated for this incident. Ensure document generation is selected during creation.")
        else:
            st.info("No reports directory found for this run.")
