"""MedSift AI — Streamlit Demo Interface.

This is a test/demo UI, NOT the final frontend.
Run with: streamlit run streamlit_demo/app.py
Requires FastAPI backend running on port 8000.
"""

import json
import requests
import streamlit as st
from datetime import date

API_BASE = "http://localhost:8000"


def api_get(endpoint: str, params: dict = None):
    """Make a GET request to the FastAPI backend."""
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error("Cannot connect to API. Make sure FastAPI is running: `uvicorn app.main:app --reload --port 8000`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(endpoint: str, data: dict = None, files: dict = None):
    """Make a POST request to the FastAPI backend."""
    try:
        if files:
            r = requests.post(f"{API_BASE}{endpoint}", files=files, timeout=300)
        else:
            r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=300)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error("Cannot connect to API. Make sure FastAPI is running.")
        return None
    except requests.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# --- Page Config ---
st.set_page_config(
    page_title="MedSift AI",
    page_icon="🏥",
    layout="wide",
)

st.title("MedSift AI")
st.caption("Sift through medical conversations. Surface what matters.")

# --- Sidebar Navigation ---
page = st.sidebar.radio(
    "Navigation",
    ["Upload & Process", "Visit History", "Analytics Dashboard"],
)


# ========================================
# PAGE: Upload & Process
# ========================================
if page == "Upload & Process":
    st.header("Upload & Process Audio")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload a patient-doctor conversation recording",
            type=["mp3", "wav", "m4a", "webm"],
        )

        visit_date = st.date_input("Visit Date", value=date.today())
        visit_type = st.selectbox(
            "Visit Type",
            ["routine checkup", "follow-up", "specialist", "urgent care", "telehealth"],
        )
        tags = st.text_input("Tags (comma-separated)", placeholder="diabetes, cardiology")

    with col2:
        st.info(
            "**How it works:**\n"
            "1. Upload audio → Whisper transcribes it\n"
            "2. PHI is automatically redacted\n"
            "3. LLM extracts care plan + SOAP note\n"
            "4. Risk scoring identifies red flags\n"
            "5. Clinical trials & literature are searched"
        )

    if uploaded_file and st.button("Process Recording", type="primary"):
        # Step 1: Transcribe
        with st.spinner("Transcribing audio with Whisper..."):
            result = api_post(
                "/api/transcribe",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())},
            )

        if result:
            st.success(f"Transcription complete ({result['duration']:.1f}s audio)")

            with st.expander("Raw Transcript", expanded=False):
                st.text(result["transcript"])

            with st.expander("Redacted Transcript (PHI removed)", expanded=True):
                st.text(result["redacted_transcript"])
                if result["entity_count"]:
                    st.caption(f"Entities redacted: {result['entity_count']}")

            # Step 2: Analyze
            with st.spinner("Analyzing with LLM (this may take 1-2 minutes)..."):
                tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                analysis = api_post("/api/analyze", data={
                    "transcript": result["redacted_transcript"],
                    "visit_date": visit_date.isoformat(),
                    "visit_type": visit_type,
                    "tags": tag_list,
                })

            if analysis:
                st.success(f"Analysis complete! Visit ID: {analysis['visit_id']}")
                st.session_state["last_visit_id"] = analysis["visit_id"]

                # Display results in tabs
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "Care Plan", "SOAP Note", "Risk Assessment", "Trials & Literature", "PDF Export"
                ])

                with tab1:
                    ps = analysis["patient_summary"]
                    st.subheader("Visit Summary")
                    st.write(ps.get("visit_summary", ""))

                    if ps.get("medications"):
                        st.subheader("Medications")
                        for med in ps["medications"]:
                            st.markdown(f"**{med['name']}** {med['dose']} — {med['frequency']}")
                            if med.get("instructions"):
                                st.caption(f"Instructions: {med['instructions']}")
                            if med.get("evidence"):
                                st.caption(f"📝 Evidence: _{med['evidence']}_")

                    if ps.get("tests_ordered"):
                        st.subheader("Tests Ordered")
                        for test in ps["tests_ordered"]:
                            st.markdown(f"**{test['test_name']}** — {test['timeline']}")
                            if test.get("evidence"):
                                st.caption(f"📝 _{test['evidence']}_")

                    if ps.get("follow_up_plan"):
                        st.subheader("Follow-Up Plan")
                        for fu in ps["follow_up_plan"]:
                            st.checkbox(f"{fu['action']} ({fu['date_or_timeline']})", key=f"fu_{fu['action']}")

                    if ps.get("lifestyle_recommendations"):
                        st.subheader("Lifestyle Recommendations")
                        for rec in ps["lifestyle_recommendations"]:
                            st.markdown(f"- **{rec['recommendation']}**: {rec.get('details', '')}")

                    if ps.get("red_flags_for_patient"):
                        st.subheader("⚠️ When to Seek Urgent Care")
                        for rf in ps["red_flags_for_patient"]:
                            st.warning(rf["warning"])

                    if ps.get("questions_and_answers"):
                        st.subheader("Questions & Answers")
                        for qa in ps["questions_and_answers"]:
                            st.markdown(f"**Q:** {qa['question']}")
                            st.markdown(f"**A:** {qa['answer']}")
                            st.divider()

                with tab2:
                    cn = analysis["clinician_note"]
                    soap = cn.get("soap_note", {})

                    st.subheader("SOAP Note")
                    with st.expander("Subjective", expanded=True):
                        s = soap.get("subjective", {})
                        st.markdown(f"**CC:** {s.get('chief_complaint', '')}")
                        st.markdown(f"**HPI:** {s.get('history_of_present_illness', '')}")
                        st.markdown(f"**ROS:** {s.get('review_of_systems', '')}")

                    with st.expander("Objective", expanded=True):
                        o = soap.get("objective", {})
                        st.markdown(f"**Vitals:** {o.get('vitals', '')}")
                        st.markdown(f"**PE:** {o.get('physical_exam_findings', '')}")

                    with st.expander("Assessment", expanded=True):
                        a = soap.get("assessment", {})
                        st.markdown(f"**Diagnoses:** {', '.join(a.get('diagnoses', []))}")
                        st.markdown(f"**Impression:** {a.get('clinical_impression', '')}")

                    with st.expander("Plan", expanded=True):
                        p = soap.get("plan", {})
                        if p.get("medications"):
                            st.markdown(f"**Medications:** {', '.join(p['medications'])}")
                        if p.get("tests_ordered"):
                            st.markdown(f"**Tests:** {', '.join(p['tests_ordered'])}")
                        if p.get("referrals"):
                            st.markdown(f"**Referrals:** {', '.join(p['referrals'])}")
                        st.markdown(f"**Follow-up:** {p.get('follow_up', '')}")

                    if cn.get("problem_list"):
                        st.subheader("Problem List")
                        for prob in cn["problem_list"]:
                            st.markdown(f"- {prob}")

                    if cn.get("action_items"):
                        st.subheader("Action Items")
                        for item in cn["action_items"]:
                            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.get("priority", ""), "")
                            st.markdown(f"{priority_icon} {item['action']}")

                with tab3:
                    ra = analysis["risk_assessment"]
                    score = ra["risk_score"]
                    level = ra["risk_level"]

                    color = {"low": "green", "medium": "orange", "high": "red"}.get(level, "gray")
                    st.markdown(f"### Risk Score: :{color}[{score}/100 ({level.upper()})]")

                    if ra.get("risk_factors"):
                        st.subheader("Risk Factors")
                        for rf in ra["risk_factors"]:
                            st.markdown(f"- **{rf['factor']}** (+{rf['points']} pts)")
                            if rf.get("evidence"):
                                st.caption(f"📝 _{rf['evidence']}_")

                    if ra.get("red_flags"):
                        st.subheader("🚨 Red Flags")
                        for flag in ra["red_flags"]:
                            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(flag.get("severity", ""), "")
                            st.error(f"{severity_icon} **{flag['flag']}**")
                            if flag.get("recommended_action"):
                                st.caption(f"Recommended: {flag['recommended_action']}")

                    st.caption(ra.get("disclaimer", ""))

                with tab4:
                    col_trials, col_papers = st.columns(2)

                    with col_trials:
                        st.subheader("Clinical Trials (Recruiting)")
                        trials = analysis.get("clinical_trials", [])
                        if trials:
                            for trial in trials:
                                st.markdown(f"**[{trial['title']}]({trial['url']})**")
                                st.caption(f"NCT: {trial['nct_id']} | Status: {trial['status']}")
                                st.caption(f"Conditions: {', '.join(trial.get('conditions', []))}")
                                st.caption(f"Why: {trial.get('match_explanation', '')}")
                                st.divider()
                        else:
                            st.info("No recruiting trials found.")

                    with col_papers:
                        st.subheader("Published Research")
                        papers = analysis.get("literature", [])
                        if papers:
                            for paper in papers:
                                st.markdown(f"**[{paper['title']}]({paper['url']})**")
                                authors = ", ".join(paper.get("authors", [])[:3])
                                if len(paper.get("authors", [])) > 3:
                                    authors += " et al."
                                st.caption(f"{authors} ({paper.get('year', 'N/A')}) | Citations: {paper.get('citation_count', 0)}")
                                if paper.get("abstract_snippet"):
                                    st.caption(paper["abstract_snippet"])
                                st.caption(f"Relevance: {paper.get('relevance_explanation', '')}")

                                # Feedback buttons
                                fcol1, fcol2 = st.columns(2)
                                with fcol1:
                                    if st.button("👍 Relevant", key=f"rel_{paper['paper_id']}"):
                                        api_post("/api/feedback", data={
                                            "visit_id": analysis["visit_id"],
                                            "feedback_type": "literature_relevance",
                                            "item_type": "paper",
                                            "item_value": paper["title"],
                                            "rating": "relevant",
                                            "paper_url": paper.get("url", ""),
                                        })
                                        st.success("Feedback recorded!")
                                with fcol2:
                                    if st.button("👎 Not relevant", key=f"nrel_{paper['paper_id']}"):
                                        api_post("/api/feedback", data={
                                            "visit_id": analysis["visit_id"],
                                            "feedback_type": "literature_relevance",
                                            "item_type": "paper",
                                            "item_value": paper["title"],
                                            "rating": "not_relevant",
                                            "paper_url": paper.get("url", ""),
                                        })
                                        st.success("Feedback recorded!")
                                st.divider()
                        else:
                            st.info("No papers found.")

                with tab5:
                    st.subheader("Export PDF")
                    if st.button("Download After Visit Summary PDF"):
                        try:
                            r = requests.get(
                                f"{API_BASE}/api/export/{analysis['visit_id']}/pdf",
                                timeout=30,
                            )
                            r.raise_for_status()
                            st.download_button(
                                "📥 Download PDF",
                                data=r.content,
                                file_name=f"MedSift_Visit_{analysis['visit_id']}_Summary.pdf",
                                mime="application/pdf",
                            )
                        except Exception as e:
                            st.error(f"PDF export failed: {e}")


# ========================================
# PAGE: Visit History
# ========================================
elif page == "Visit History":
    st.header("Visit History")

    search = st.text_input("Search visits", placeholder="Search transcripts...")
    data = api_get("/api/visits", params={"search": search} if search else None)

    if data and data.get("visits"):
        for visit in data["visits"]:
            with st.expander(
                f"Visit #{visit['id']} — {visit.get('visit_date', 'N/A')} "
                f"({visit.get('visit_type', 'N/A')})"
            ):
                if visit.get("tags"):
                    st.caption(f"Tags: {', '.join(visit['tags'])}")

                if visit.get("patient_summary"):
                    ps = visit["patient_summary"]
                    st.markdown(f"**Summary:** {ps.get('visit_summary', '')}")

                    if ps.get("medications"):
                        st.markdown("**Medications:**")
                        for med in ps["medications"]:
                            st.markdown(f"- {med['name']} {med.get('dose', '')}")

                            # Feedback buttons for extraction accuracy
                            fcol1, fcol2, fcol3 = st.columns(3)
                            with fcol1:
                                if st.button("✅ Correct", key=f"c_{visit['id']}_{med['name']}"):
                                    api_post("/api/feedback", data={
                                        "visit_id": visit["id"],
                                        "feedback_type": "extraction_accuracy",
                                        "item_type": "medication",
                                        "item_value": f"{med['name']} {med.get('dose', '')}",
                                        "rating": "correct",
                                    })
                                    st.success("Feedback recorded!")
                            with fcol2:
                                if st.button("❌ Incorrect", key=f"i_{visit['id']}_{med['name']}"):
                                    api_post("/api/feedback", data={
                                        "visit_id": visit["id"],
                                        "feedback_type": "extraction_accuracy",
                                        "item_type": "medication",
                                        "item_value": f"{med['name']} {med.get('dose', '')}",
                                        "rating": "incorrect",
                                    })
                                    st.success("Feedback recorded!")

                if visit.get("risk_assessment"):
                    ra = visit["risk_assessment"]
                    level = ra.get("risk_level", "low")
                    color = {"low": "green", "medium": "orange", "high": "red"}.get(level, "gray")
                    st.markdown(f"**Risk:** :{color}[{ra.get('risk_score', 0)}/100 ({level.upper()})]")

                # Export button
                if st.button(f"📥 Export PDF", key=f"pdf_{visit['id']}"):
                    try:
                        r = requests.get(f"{API_BASE}/api/export/{visit['id']}/pdf", timeout=30)
                        r.raise_for_status()
                        st.download_button(
                            "Download",
                            data=r.content,
                            file_name=f"MedSift_Visit_{visit['id']}.pdf",
                            mime="application/pdf",
                            key=f"dl_{visit['id']}",
                        )
                    except Exception as e:
                        st.error(f"PDF export failed: {e}")
    else:
        st.info("No visits yet. Upload and process an audio recording to get started.")


# ========================================
# PAGE: Analytics Dashboard
# ========================================
elif page == "Analytics Dashboard":
    st.header("Analytics Dashboard")

    analytics = api_get("/api/analytics")
    fb_analytics = api_get("/api/feedback/analytics")

    if analytics:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Visits", analytics.get("total_visits", 0))
        with col2:
            st.metric("Avg Risk Score", f"{analytics.get('average_risk_score', 0):.1f}")
        with col3:
            acc = analytics.get("extraction_accuracy_rate", 0)
            st.metric("Extraction Accuracy", f"{acc:.0%}" if acc else "N/A")
        with col4:
            rel = analytics.get("literature_relevance_rate", 0)
            st.metric("Literature Relevance", f"{rel:.0%}" if rel else "N/A")

        # Risk distribution
        risk_dist = analytics.get("risk_distribution", {})
        if any(risk_dist.values()):
            st.subheader("Risk Level Distribution")
            st.bar_chart(risk_dist)

        # Most common conditions
        conditions = analytics.get("most_common_conditions", [])
        if conditions:
            st.subheader("Most Common Conditions")
            cond_data = {c["condition"]: c["count"] for c in conditions}
            st.bar_chart(cond_data)

        # Most common medications
        meds = analytics.get("most_common_medications", [])
        if meds:
            st.subheader("Most Common Medications")
            med_data = {m["medication"]: m["count"] for m in meds}
            st.bar_chart(med_data)

        # Visits over time
        timeline = analytics.get("visits_over_time", [])
        if timeline:
            st.subheader("Visits Over Time")
            time_data = {t["month"]: t["count"] for t in timeline}
            st.bar_chart(time_data)

        # Boosted keywords
        keywords = analytics.get("top_boosted_keywords", [])
        if keywords:
            st.subheader("Top Boosted Keywords (from feedback)")
            st.write(", ".join(keywords))

    if fb_analytics:
        st.subheader("Feedback Analytics")

        # Accuracy by item type
        acc_by_type = fb_analytics.get("accuracy_by_item_type", {})
        if acc_by_type:
            st.markdown("**Extraction Accuracy by Item Type:**")
            for item_type, rate in acc_by_type.items():
                st.progress(rate, text=f"{item_type}: {rate:.0%}")

        # Most relevant papers
        top_papers = fb_analytics.get("most_relevant_papers", [])
        if top_papers:
            st.markdown("**Most Highly Rated Papers:**")
            for paper in top_papers[:5]:
                st.markdown(
                    f"- {paper['title']} "
                    f"(👍 {paper['positive_votes']}/{paper['total_votes']})"
                )

        # Most useful keywords
        useful_kw = fb_analytics.get("most_useful_keywords", [])
        if useful_kw:
            st.markdown(f"**Most Useful Keywords:** {', '.join(useful_kw)}")

    if not analytics and not fb_analytics:
        st.info("No data yet. Process some visits to see analytics.")
