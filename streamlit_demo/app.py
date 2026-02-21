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


def _bullets_to_text(items: list) -> str:
    """Convert a list of bullet strings to text (one per line)."""
    return "\n".join(items) if items else ""


def _text_to_bullets(text: str) -> list:
    """Convert text area content (one item per line) to list of strings."""
    if not text or not text.strip():
        return []
    return [line.lstrip("- ").strip() for line in text.strip().split("\n") if line.strip()]


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


def api_put(endpoint: str, data: dict = None):
    """Make a PUT request to the FastAPI backend."""
    try:
        r = requests.put(f"{API_BASE}{endpoint}", json=data, timeout=30)
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
    ["Upload & Process", "Live Transcription", "Visit History", "Analytics Dashboard"],
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
            "4. Clinical trials & literature are searched"
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

                # Store analysis for review
                st.session_state["pending_analysis"] = analysis

                # Display results in tabs
                tab1, tab2, tab3, tab4 = st.tabs([
                    "Care Plan", "SOAP Note", "Trials & Literature", "Review & Approve"
                ])

                with tab1:
                    ps = analysis["patient_summary"]
                    st.subheader("Patient Letter")
                    st.markdown(ps.get("visit_summary", "").replace("\n", "  \n"))

                    if ps.get("medications"):
                        st.subheader("Medications")
                        for med in ps["medications"]:
                            verified = med.get("verified", True)
                            badge = "Verified" if verified else "Unverified"
                            st.markdown(f"**{med['name']}** {med['dose']} — {med['frequency']}")
                            if med.get("instructions"):
                                st.caption(f"Instructions: {med['instructions']}")
                            if med.get("evidence"):
                                st.caption(f"📝 Evidence: _{med['evidence']}_")
                            if not verified:
                                st.caption("⚠️ _Could not verify against transcript_")

                    if ps.get("tests_ordered"):
                        st.subheader("Tests Ordered")
                        for test in ps["tests_ordered"]:
                            st.markdown(f"**{test['test_name']}** — {test['timeline']}")
                            if test.get("evidence"):
                                st.caption(f"📝 _{test['evidence']}_")
                            if not test.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")

                    if ps.get("follow_up_plan"):
                        st.subheader("Follow-Up Plan")
                        for fu in ps["follow_up_plan"]:
                            st.markdown(f"- [ ] **{fu['action']}** — {fu['date_or_timeline']}")
                            if not fu.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")

                    if ps.get("lifestyle_recommendations"):
                        st.subheader("Lifestyle Recommendations")
                        for rec in ps["lifestyle_recommendations"]:
                            st.markdown(f"- **{rec['recommendation']}**: {rec.get('details', '')}")
                            if not rec.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")

                    if ps.get("red_flags_for_patient"):
                        st.subheader("⚠️ When to Seek Urgent Care")
                        for rf in ps["red_flags_for_patient"]:
                            st.warning(rf["warning"])
                            if not rf.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")

                    if ps.get("questions_and_answers"):
                        st.subheader("Questions & Answers")
                        for qa in ps["questions_and_answers"]:
                            st.markdown(f"**Q:** {qa['question']}")
                            st.markdown(f"**A:** {qa['answer']}")
                            if not qa.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")
                            st.divider()

                with tab2:
                    cn = analysis["clinician_note"]
                    soap = cn.get("soap_note", {})
                    vid = analysis.get("visit_id")

                    st.subheader("SOAP Note")
                    st.caption("Edit any section below to add missing details. One finding per line.")

                    s = soap.get("subjective", {})
                    o = soap.get("objective", {})
                    a = soap.get("assessment", {})
                    p = soap.get("plan", {})

                    soap_subj = st.text_area(
                        "S: Subjective",
                        value=_bullets_to_text(s.get("findings", [])),
                        key="soap_subj",
                        height=200,
                    )

                    st.markdown("**O: Objective**")
                    soap_vitals = st.text_area(
                        "Vital signs",
                        value=_bullets_to_text(o.get("vital_signs", [])),
                        key="soap_vitals",
                        height=80,
                        placeholder="e.g. BP: 120/80, HR: 72",
                    )
                    soap_pe = st.text_area(
                        "Physical Examination",
                        value=_bullets_to_text(o.get("physical_exam", [])),
                        key="soap_pe",
                        height=120,
                    )
                    soap_mse = st.text_area(
                        "Mental state examination",
                        value=_bullets_to_text(o.get("mental_state_exam", [])),
                        key="soap_mse",
                        height=80,
                        placeholder="Optional — leave blank if not assessed",
                    )
                    soap_labs = st.text_area(
                        "Lab results",
                        value=_bullets_to_text(o.get("lab_results", [])),
                        key="soap_labs",
                        height=80,
                        placeholder="Optional — leave blank if none",
                    )

                    soap_assess = st.text_area(
                        "A: Assessment",
                        value=_bullets_to_text(a.get("findings", [])),
                        key="soap_assess",
                        height=100,
                    )

                    soap_plan = st.text_area(
                        "P: Plan",
                        value=_bullets_to_text(p.get("findings", [])),
                        key="soap_plan",
                        height=150,
                    )

                    soap_problems = st.text_area(
                        "Problem List",
                        value=_bullets_to_text(cn.get("problem_list", [])),
                        key="soap_problems",
                        height=80,
                    )

                    if cn.get("action_items"):
                        st.subheader("Action Items")
                        for item in cn["action_items"]:
                            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.get("priority", ""), "")
                            st.markdown(f"{priority_icon} {item['action']}")
                            if not item.get("verified", True):
                                st.caption("⚠️ _Could not verify against transcript_")

                    if vid and st.button("Save SOAP Note", type="primary", key="save_soap"):
                        updated_note = {
                            "soap_note": {
                                "subjective": {
                                    "findings": _text_to_bullets(soap_subj),
                                    "evidence": s.get("evidence", []),
                                },
                                "objective": {
                                    "vital_signs": _text_to_bullets(soap_vitals),
                                    "physical_exam": _text_to_bullets(soap_pe),
                                    "mental_state_exam": _text_to_bullets(soap_mse),
                                    "lab_results": _text_to_bullets(soap_labs),
                                    "evidence": o.get("evidence", []),
                                },
                                "assessment": {
                                    "findings": _text_to_bullets(soap_assess),
                                    "evidence": a.get("evidence", []),
                                },
                                "plan": {
                                    "findings": _text_to_bullets(soap_plan),
                                    "evidence": p.get("evidence", []),
                                },
                            },
                            "problem_list": _text_to_bullets(soap_problems),
                            "action_items": cn.get("action_items", []),
                        }
                        result = api_put(
                            f"/api/visits/{vid}/clinician-note",
                            data=updated_note,
                        )
                        if result:
                            st.success("SOAP note saved successfully.")

                with tab3:
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

                with tab4:
                    st.subheader("Review & Approve for Patient")
                    st.caption(
                        "Review each extracted item below. Uncheck items that are "
                        "incorrect or should not appear in the patient's After Visit Summary. "
                        "Only approved items will be included in the PDF."
                    )

                    ps = analysis["patient_summary"]

                    # Visit summary letter (always included, editable)
                    st.caption(
                        "Edit the patient letter below. Replace [Patient's Name], "
                        "[Doctor's Name], and [Contact Information] with actual values."
                    )
                    reviewed_summary = st.text_area(
                        "Patient Letter",
                        value=ps.get("visit_summary", ""),
                        key="review_visit_summary",
                        height=300,
                    )

                    # Medications review
                    approved_meds = []
                    if ps.get("medications"):
                        st.markdown("**Medications:**")
                        for i, med in enumerate(ps["medications"]):
                            verified = med.get("verified", True)
                            label = f"{med['name']} {med.get('dose', '')} — {med.get('frequency', '')}"
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_med_{i}"):
                                approved_meds.append(med)

                    # Tests review
                    approved_tests = []
                    if ps.get("tests_ordered"):
                        st.markdown("**Tests Ordered:**")
                        for i, test in enumerate(ps["tests_ordered"]):
                            verified = test.get("verified", True)
                            label = f"{test['test_name']} — {test.get('timeline', '')}"
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_test_{i}"):
                                approved_tests.append(test)

                    # Follow-ups review
                    approved_followups = []
                    if ps.get("follow_up_plan"):
                        st.markdown("**Follow-Up Plan:**")
                        for i, fu in enumerate(ps["follow_up_plan"]):
                            verified = fu.get("verified", True)
                            label = f"{fu['action']} — {fu.get('date_or_timeline', '')}"
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_fu_{i}"):
                                approved_followups.append(fu)

                    # Lifestyle recommendations review
                    approved_lifestyle = []
                    if ps.get("lifestyle_recommendations"):
                        st.markdown("**Lifestyle Recommendations:**")
                        for i, rec in enumerate(ps["lifestyle_recommendations"]):
                            verified = rec.get("verified", True)
                            label = rec["recommendation"]
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_life_{i}"):
                                approved_lifestyle.append(rec)

                    # Red flags review
                    approved_flags = []
                    if ps.get("red_flags_for_patient"):
                        st.markdown("**Red Flags / Urgent Care Warnings:**")
                        for i, rf in enumerate(ps["red_flags_for_patient"]):
                            verified = rf.get("verified", True)
                            label = rf["warning"]
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_rf_{i}"):
                                approved_flags.append(rf)

                    # Q&A review
                    approved_qa = []
                    if ps.get("questions_and_answers"):
                        st.markdown("**Questions & Answers:**")
                        for i, qa in enumerate(ps["questions_and_answers"]):
                            verified = qa.get("verified", True)
                            label = f"Q: {qa['question']}"
                            if not verified:
                                label += " ⚠️ unverified"
                            if st.checkbox(label, value=True, key=f"rev_qa_{i}"):
                                approved_qa.append(qa)

                    st.divider()

                    include_soap_in_pdf = st.checkbox(
                        "Include SOAP Note in PDF",
                        value=False,
                        key="review_include_soap",
                        help="Include the clinician SOAP note (with any edits) in the patient PDF.",
                    )

                    # Approve and generate
                    if st.button("Approve & Generate PDF", type="primary"):
                        approved_summary = {
                            "visit_summary": reviewed_summary,
                            "medications": approved_meds,
                            "tests_ordered": approved_tests,
                            "follow_up_plan": approved_followups,
                            "lifestyle_recommendations": approved_lifestyle,
                            "red_flags_for_patient": approved_flags,
                            "questions_and_answers": approved_qa,
                        }
                        try:
                            r = requests.post(
                                f"{API_BASE}/api/export/reviewed/pdf",
                                json={
                                    "visit_id": analysis["visit_id"],
                                    "approved_summary": approved_summary,
                                    "include_soap": include_soap_in_pdf,
                                },
                                timeout=30,
                            )
                            r.raise_for_status()
                            st.download_button(
                                "📥 Download Approved After Visit Summary",
                                data=r.content,
                                file_name=f"MedSift_Visit_{analysis['visit_id']}_Approved.pdf",
                                mime="application/pdf",
                            )
                            st.success("PDF generated with doctor-approved items only.")
                        except Exception as e:
                            st.error(f"PDF generation failed: {e}")


# ========================================
# PAGE: Live Transcription
# ========================================
elif page == "Live Transcription":
    from live_transcribe_component import render_live_transcription_tab
    render_live_transcription_tab()


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
                    summary_preview = ps.get("visit_summary", "")
                    # Show first 200 chars as preview
                    if len(summary_preview) > 200:
                        st.markdown(f"**Summary:** {summary_preview[:200]}...")
                    else:
                        st.markdown(f"**Summary:** {summary_preview}")

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

                # Editable SOAP Note
                if visit.get("clinician_note"):
                    cn = visit["clinician_note"]
                    soap = cn.get("soap_note", {})
                    vid = visit["id"]
                    soap_key = f"soap_edit_{vid}"

                    if st.button("Edit SOAP Note", key=f"btn_soap_{vid}"):
                        st.session_state[soap_key] = True

                    if st.session_state.get(soap_key):
                        st.markdown("---")
                        st.subheader("Edit SOAP Note")
                        st.caption("One finding per line. Add missing details from the visit.")

                        s = soap.get("subjective", {})
                        o = soap.get("objective", {})
                        a = soap.get("assessment", {})
                        p = soap.get("plan", {})

                        h_subj = st.text_area(
                            "S: Subjective",
                            value=_bullets_to_text(s.get("findings", [])),
                            key=f"h_soap_subj_{vid}",
                            height=200,
                        )
                        st.markdown("**O: Objective**")
                        h_vitals = st.text_area(
                            "Vital signs",
                            value=_bullets_to_text(o.get("vital_signs", [])),
                            key=f"h_soap_vitals_{vid}",
                            height=80,
                            placeholder="e.g. BP: 120/80, HR: 72",
                        )
                        h_pe = st.text_area(
                            "Physical Examination",
                            value=_bullets_to_text(o.get("physical_exam", [])),
                            key=f"h_soap_pe_{vid}",
                            height=120,
                        )
                        h_mse = st.text_area(
                            "Mental state examination",
                            value=_bullets_to_text(o.get("mental_state_exam", [])),
                            key=f"h_soap_mse_{vid}",
                            height=80,
                            placeholder="Optional",
                        )
                        h_labs = st.text_area(
                            "Lab results",
                            value=_bullets_to_text(o.get("lab_results", [])),
                            key=f"h_soap_labs_{vid}",
                            height=80,
                            placeholder="Optional",
                        )
                        h_assess = st.text_area(
                            "A: Assessment",
                            value=_bullets_to_text(a.get("findings", [])),
                            key=f"h_soap_assess_{vid}",
                            height=100,
                        )
                        h_plan = st.text_area(
                            "P: Plan",
                            value=_bullets_to_text(p.get("findings", [])),
                            key=f"h_soap_plan_{vid}",
                            height=150,
                        )
                        h_problems = st.text_area(
                            "Problem List",
                            value=_bullets_to_text(cn.get("problem_list", [])),
                            key=f"h_soap_problems_{vid}",
                            height=80,
                        )

                        if st.button("Save SOAP Note", type="primary", key=f"h_save_soap_{vid}"):
                            updated_note = {
                                "soap_note": {
                                    "subjective": {
                                        "findings": _text_to_bullets(h_subj),
                                        "evidence": s.get("evidence", []),
                                    },
                                    "objective": {
                                        "vital_signs": _text_to_bullets(h_vitals),
                                        "physical_exam": _text_to_bullets(h_pe),
                                        "mental_state_exam": _text_to_bullets(h_mse),
                                        "lab_results": _text_to_bullets(h_labs),
                                        "evidence": o.get("evidence", []),
                                    },
                                    "assessment": {
                                        "findings": _text_to_bullets(h_assess),
                                        "evidence": a.get("evidence", []),
                                    },
                                    "plan": {
                                        "findings": _text_to_bullets(h_plan),
                                        "evidence": p.get("evidence", []),
                                    },
                                },
                                "problem_list": _text_to_bullets(h_problems),
                                "action_items": cn.get("action_items", []),
                            }
                            result = api_put(
                                f"/api/visits/{vid}/clinician-note",
                                data=updated_note,
                            )
                            if result:
                                st.success("SOAP note saved successfully.")

                # Review & Approve before PDF export
                if visit.get("patient_summary"):
                    review_key = f"review_{visit['id']}"
                    if st.button("Review & Approve for PDF", key=f"btn_review_{visit['id']}"):
                        st.session_state[review_key] = True

                    if st.session_state.get(review_key):
                        st.markdown("---")
                        st.subheader("Review & Approve for Patient")
                        st.caption(
                            "Uncheck items that are incorrect or should not appear "
                            "in the patient's After Visit Summary."
                        )
                        ps = visit["patient_summary"]
                        vid = visit["id"]

                        st.caption(
                            "Edit the patient letter below. Replace [Patient's Name], "
                            "[Doctor's Name], and [Contact Information] with actual values."
                        )
                        reviewed_summary = st.text_area(
                            "Patient Letter",
                            value=ps.get("visit_summary", ""),
                            key=f"hist_summary_{vid}",
                            height=300,
                        )

                        approved_meds = []
                        if ps.get("medications"):
                            st.markdown("**Medications:**")
                            for i, med in enumerate(ps["medications"]):
                                verified = med.get("verified", True)
                                label = f"{med['name']} {med.get('dose', '')} — {med.get('frequency', '')}"
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_med_{vid}_{i}"):
                                    approved_meds.append(med)

                        approved_tests = []
                        if ps.get("tests_ordered"):
                            st.markdown("**Tests Ordered:**")
                            for i, test in enumerate(ps["tests_ordered"]):
                                verified = test.get("verified", True)
                                label = f"{test['test_name']} — {test.get('timeline', '')}"
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_test_{vid}_{i}"):
                                    approved_tests.append(test)

                        approved_followups = []
                        if ps.get("follow_up_plan"):
                            st.markdown("**Follow-Up Plan:**")
                            for i, fu in enumerate(ps["follow_up_plan"]):
                                verified = fu.get("verified", True)
                                label = f"{fu['action']} — {fu.get('date_or_timeline', '')}"
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_fu_{vid}_{i}"):
                                    approved_followups.append(fu)

                        approved_lifestyle = []
                        if ps.get("lifestyle_recommendations"):
                            st.markdown("**Lifestyle Recommendations:**")
                            for i, rec in enumerate(ps["lifestyle_recommendations"]):
                                verified = rec.get("verified", True)
                                label = rec["recommendation"]
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_life_{vid}_{i}"):
                                    approved_lifestyle.append(rec)

                        approved_flags = []
                        if ps.get("red_flags_for_patient"):
                            st.markdown("**Red Flags / Urgent Care Warnings:**")
                            for i, rf in enumerate(ps["red_flags_for_patient"]):
                                verified = rf.get("verified", True)
                                label = rf["warning"]
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_rf_{vid}_{i}"):
                                    approved_flags.append(rf)

                        approved_qa = []
                        if ps.get("questions_and_answers"):
                            st.markdown("**Questions & Answers:**")
                            for i, qa in enumerate(ps["questions_and_answers"]):
                                verified = qa.get("verified", True)
                                label = f"Q: {qa['question']}"
                                if not verified:
                                    label += " ⚠️ unverified"
                                if st.checkbox(label, value=True, key=f"hist_qa_{vid}_{i}"):
                                    approved_qa.append(qa)

                        st.divider()
                        hist_include_soap = st.checkbox(
                            "Include SOAP Note in PDF",
                            value=False,
                            key=f"hist_include_soap_{vid}",
                            help="Include the clinician SOAP note (with any edits) in the patient PDF.",
                        )
                        if st.button("Approve & Generate PDF", type="primary", key=f"hist_approve_{vid}"):
                            approved_summary = {
                                "visit_summary": reviewed_summary,
                                "medications": approved_meds,
                                "tests_ordered": approved_tests,
                                "follow_up_plan": approved_followups,
                                "lifestyle_recommendations": approved_lifestyle,
                                "red_flags_for_patient": approved_flags,
                                "questions_and_answers": approved_qa,
                            }
                            try:
                                r = requests.post(
                                    f"{API_BASE}/api/export/reviewed/pdf",
                                    json={
                                        "visit_id": vid,
                                        "approved_summary": approved_summary,
                                        "include_soap": hist_include_soap,
                                    },
                                    timeout=30,
                                )
                                r.raise_for_status()
                                st.download_button(
                                    "📥 Download Approved After Visit Summary",
                                    data=r.content,
                                    file_name=f"MedSift_Visit_{vid}_Approved.pdf",
                                    mime="application/pdf",
                                    key=f"hist_dl_{vid}",
                                )
                                st.success("PDF generated with doctor-approved items only.")
                            except Exception as e:
                                st.error(f"PDF generation failed: {e}")
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Visits", analytics.get("total_visits", 0))
        with col2:
            acc = analytics.get("extraction_accuracy_rate", 0)
            st.metric("Extraction Accuracy", f"{acc:.0%}" if acc else "N/A")
        with col3:
            rel = analytics.get("literature_relevance_rate", 0)
            st.metric("Literature Relevance", f"{rel:.0%}" if rel else "N/A")

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
