"""SQLite database setup, models, and CRUD operations."""

import json
import re
import os
import sqlite3
from datetime import datetime, date
from typing import Optional

from models.schemas import (
    VisitRecord, PatientSummary, ClinicianNote,
    ClinicalTrial, LiteratureResult, TranscriptSegment,
    FeedbackItem, FeedbackAnalytics, BoostedKeyword, AnalyticsSummary,
)
from app.config import DATABASE_PATH


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visit_date DATE,
                visit_type TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                audio_duration_seconds REAL DEFAULT 0.0,
                raw_transcript TEXT DEFAULT '',
                patient_summary_json TEXT,
                clinician_note_json TEXT,
                clinical_trials_json TEXT DEFAULT '[]',
                literature_results_json TEXT DEFAULT '[]',
                transcript_segments_json TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_id INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_value TEXT NOT NULL,
                rating TEXT NOT NULL,
                paper_url TEXT,
                clinician_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (visit_id) REFERENCES visits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS keyword_boost (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                boost_score REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create FTS5 virtual table for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS visits_fts USING fts5(
                raw_transcript, tags, content=visits, content_rowid=id
            )
        """)

        # Create triggers to keep FTS in sync
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS visits_ai AFTER INSERT ON visits BEGIN
                INSERT INTO visits_fts(rowid, raw_transcript, tags)
                VALUES (new.id, new.raw_transcript, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS visits_ad AFTER DELETE ON visits BEGIN
                INSERT INTO visits_fts(visits_fts, rowid, raw_transcript, tags)
                VALUES ('delete', old.id, old.raw_transcript, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS visits_au AFTER UPDATE ON visits BEGIN
                INSERT INTO visits_fts(visits_fts, rowid, raw_transcript, tags)
                VALUES ('delete', old.id, old.raw_transcript, old.tags);
                INSERT INTO visits_fts(rowid, raw_transcript, tags)
                VALUES (new.id, new.raw_transcript, new.tags);
            END;
        """)

        conn.commit()
    finally:
        conn.close()


def _serialize_optional(obj) -> Optional[str]:
    """Serialize a Pydantic model to JSON string, or return None."""
    if obj is None:
        return None
    return obj.model_dump_json()


def _serialize_list(items: list) -> str:
    """Serialize a list of Pydantic models to JSON string."""
    return json.dumps([item.model_dump() for item in items])


def save_visit(visit: VisitRecord) -> int:
    """Save a visit record and return its ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO visits (
                visit_date, visit_type, tags, audio_duration_seconds,
                raw_transcript, patient_summary_json, clinician_note_json,
                clinical_trials_json,
                literature_results_json, transcript_segments_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                visit.visit_date.isoformat() if visit.visit_date else None,
                visit.visit_type,
                json.dumps(visit.tags),
                visit.audio_duration_seconds,
                visit.raw_transcript,
                _serialize_optional(visit.patient_summary),
                _serialize_optional(visit.clinician_note),
                _serialize_list(visit.clinical_trials),
                _serialize_list(visit.literature_results),
                _serialize_list(visit.transcript_segments),
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _row_to_visit(row: sqlite3.Row) -> VisitRecord:
    """Convert a database row to a VisitRecord."""
    visit_date = None
    if row["visit_date"]:
        try:
            visit_date = date.fromisoformat(row["visit_date"])
        except (ValueError, TypeError):
            pass

    created_at = None
    if row["created_at"]:
        try:
            created_at = datetime.fromisoformat(row["created_at"])
        except (ValueError, TypeError):
            pass

    return VisitRecord(
        id=row["id"],
        created_at=created_at,
        visit_date=visit_date,
        visit_type=row["visit_type"] or "",
        tags=json.loads(row["tags"]) if row["tags"] else [],
        audio_duration_seconds=row["audio_duration_seconds"] or 0.0,
        raw_transcript=row["raw_transcript"] or "",
        patient_summary=PatientSummary.model_validate_json(row["patient_summary_json"])
            if row["patient_summary_json"] else None,
        clinician_note=ClinicianNote.model_validate_json(row["clinician_note_json"])
            if row["clinician_note_json"] else None,
        clinical_trials=[ClinicalTrial.model_validate(t) for t in json.loads(row["clinical_trials_json"] or "[]")],
        literature_results=[LiteratureResult.model_validate(r) for r in json.loads(row["literature_results_json"] or "[]")],
        transcript_segments=[TranscriptSegment.model_validate(s) for s in json.loads(row["transcript_segments_json"] or "[]")],
    )


def get_visit(visit_id: int) -> Optional[VisitRecord]:
    """Get a single visit by ID."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            return None
        return _row_to_visit(row)
    finally:
        conn.close()


def get_all_visits(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "date",
    limit: int = 50,
    offset: int = 0,
) -> list[VisitRecord]:
    """Get all visits with optional search, tag filter, and sorting."""
    conn = _get_connection()
    try:
        if search:
            # Use FTS5 for full-text search
            rows = conn.execute(
                """SELECT v.* FROM visits v
                   JOIN visits_fts fts ON v.id = fts.rowid
                   WHERE visits_fts MATCH ?
                   ORDER BY v.created_at DESC
                   LIMIT ? OFFSET ?""",
                (search, limit, offset)
            ).fetchall()
        elif tag:
            rows = conn.execute(
                """SELECT * FROM visits
                   WHERE tags LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (f'%"{tag}"%', limit, offset)
            ).fetchall()
        else:
            order = "created_at DESC" if sort == "date" else "id DESC"
            rows = conn.execute(
                f"SELECT * FROM visits ORDER BY {order} LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [_row_to_visit(row) for row in rows]
    finally:
        conn.close()


def search_visits(query: str) -> list[VisitRecord]:
    """Full-text search across visits."""
    return get_all_visits(search=query)


def delete_visit(visit_id: int) -> bool:
    """Delete a visit by ID. Returns True if deleted."""
    conn = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM visits WHERE id = ?", (visit_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_clinician_note(visit_id: int, clinician_note: ClinicianNote) -> bool:
    """Update the clinician note (SOAP) for a visit. Returns True if updated."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE visits SET clinician_note_json = ? WHERE id = ?",
            (json.dumps(clinician_note.model_dump()), visit_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_patient_summary(visit_id: int, patient_summary: PatientSummary) -> bool:
    """Update the patient summary for a visit. Returns True if updated."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE visits SET patient_summary_json = ? WHERE id = ?",
            (json.dumps(patient_summary.model_dump()), visit_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def save_feedback(feedback: FeedbackItem) -> int:
    """Save a feedback entry and return its ID."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO feedback (visit_id, feedback_type, item_type, item_value, rating, paper_url, clinician_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (feedback.visit_id, feedback.feedback_type, feedback.item_type,
             feedback.item_value, feedback.rating, feedback.paper_url, feedback.clinician_note)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_feedback(visit_id: int) -> list[FeedbackItem]:
    """Get all feedback for a visit."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM feedback WHERE visit_id = ? ORDER BY created_at DESC",
            (visit_id,)
        ).fetchall()
        return [
            FeedbackItem(
                feedback_id=row["id"],
                visit_id=row["visit_id"],
                feedback_type=row["feedback_type"],
                item_type=row["item_type"],
                item_value=row["item_value"],
                rating=row["rating"],
                paper_url=row["paper_url"],
                clinician_note=row["clinician_note"],
                timestamp=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]
    finally:
        conn.close()


def update_keyword_boost(keywords: list[str], positive: bool) -> None:
    """Update keyword boost scores based on feedback."""
    conn = _get_connection()
    try:
        for keyword in keywords:
            keyword = keyword.lower().strip()
            if len(keyword) < 3:
                continue
            existing = conn.execute(
                "SELECT * FROM keyword_boost WHERE keyword = ?", (keyword,)
            ).fetchone()
            if existing:
                if positive:
                    conn.execute(
                        """UPDATE keyword_boost SET positive_count = positive_count + 1,
                           boost_score = CAST(positive_count + 1 AS REAL) / (positive_count + 1 + negative_count),
                           last_updated = CURRENT_TIMESTAMP
                           WHERE keyword = ?""",
                        (keyword,)
                    )
                else:
                    conn.execute(
                        """UPDATE keyword_boost SET negative_count = negative_count + 1,
                           boost_score = CAST(positive_count AS REAL) / (positive_count + negative_count + 1),
                           last_updated = CURRENT_TIMESTAMP
                           WHERE keyword = ?""",
                        (keyword,)
                    )
            else:
                pos = 1 if positive else 0
                neg = 0 if positive else 1
                score = pos / (pos + neg)
                conn.execute(
                    """INSERT INTO keyword_boost (keyword, positive_count, negative_count, boost_score)
                       VALUES (?, ?, ?, ?)""",
                    (keyword, pos, neg, score)
                )
        conn.commit()
    finally:
        conn.close()


def get_boosted_keywords(min_score: float = 0.0) -> list[BoostedKeyword]:
    """Get keywords with boost scores, ordered by score descending."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM keyword_boost
               WHERE boost_score >= ?
               ORDER BY boost_score DESC, positive_count DESC
               LIMIT 50""",
            (min_score,)
        ).fetchall()
        return [
            BoostedKeyword(
                keyword=row["keyword"],
                positive_count=row["positive_count"],
                negative_count=row["negative_count"],
                boost_score=row["boost_score"],
            )
            for row in rows
        ]
    finally:
        conn.close()


def get_feedback_analytics() -> FeedbackAnalytics:
    """Compute aggregated feedback analytics."""
    conn = _get_connection()
    try:
        # Total feedback count
        total = conn.execute("SELECT COUNT(*) as cnt FROM feedback").fetchone()["cnt"]

        # Extraction accuracy rate
        extraction_rows = conn.execute(
            """SELECT rating, COUNT(*) as cnt FROM feedback
               WHERE feedback_type = 'extraction_accuracy'
               GROUP BY rating"""
        ).fetchall()
        extraction_total = sum(r["cnt"] for r in extraction_rows)
        extraction_correct = sum(r["cnt"] for r in extraction_rows if r["rating"] == "correct")
        extraction_accuracy = extraction_correct / extraction_total if extraction_total > 0 else 0.0

        # Accuracy by item type
        accuracy_by_type = {}
        item_types = conn.execute(
            "SELECT DISTINCT item_type FROM feedback WHERE feedback_type = 'extraction_accuracy'"
        ).fetchall()
        for it in item_types:
            itype = it["item_type"]
            type_rows = conn.execute(
                """SELECT rating, COUNT(*) as cnt FROM feedback
                   WHERE feedback_type = 'extraction_accuracy' AND item_type = ?
                   GROUP BY rating""",
                (itype,)
            ).fetchall()
            type_total = sum(r["cnt"] for r in type_rows)
            type_correct = sum(r["cnt"] for r in type_rows if r["rating"] == "correct")
            accuracy_by_type[itype] = type_correct / type_total if type_total > 0 else 0.0

        # Literature relevance rate
        lit_rows = conn.execute(
            """SELECT rating, COUNT(*) as cnt FROM feedback
               WHERE feedback_type = 'literature_relevance'
               GROUP BY rating"""
        ).fetchall()
        lit_total = sum(r["cnt"] for r in lit_rows)
        lit_relevant = sum(r["cnt"] for r in lit_rows if r["rating"] == "relevant")
        lit_rate = lit_relevant / lit_total if lit_total > 0 else 0.0

        # Most relevant papers
        top_papers = conn.execute(
            """SELECT item_value,
                      SUM(CASE WHEN rating = 'relevant' THEN 1 ELSE 0 END) as positive_votes,
                      COUNT(*) as total_votes
               FROM feedback
               WHERE feedback_type = 'literature_relevance'
               GROUP BY item_value
               ORDER BY positive_votes DESC
               LIMIT 10"""
        ).fetchall()

        # Most useful keywords from keyword_boost
        top_kw = conn.execute(
            "SELECT keyword FROM keyword_boost ORDER BY boost_score DESC LIMIT 10"
        ).fetchall()

        return FeedbackAnalytics(
            total_feedback_count=total,
            extraction_accuracy_rate=round(extraction_accuracy, 3),
            literature_relevance_rate=round(lit_rate, 3),
            accuracy_by_item_type=accuracy_by_type,
            most_relevant_papers=[
                {"title": r["item_value"], "positive_votes": r["positive_votes"], "total_votes": r["total_votes"]}
                for r in top_papers
            ],
            most_useful_keywords=[r["keyword"] for r in top_kw],
        )
    finally:
        conn.close()



def _clean_condition(raw: str) -> list[str]:
    """Clean verbose assessment findings into short condition names."""
    if not raw or len(raw) < 3:
        return []
    # Skip junk entries entirely
    skip_patterns = [
        r'(?i)differential diagnosis', r'(?i)clinical impression', r'(?i)clinical reasoning',
        r'(?i)none mentioned', r'(?i)not mentioned', r'(?i)no .* mentioned',
        r'(?i)if mentioned', r'(?i)the patient', r'(?i)patient.s symptoms',
    ]
    for pat in skip_patterns:
        if re.search(pat, raw):
            return []
    # Remove verbose prefixes
    cleaned = re.sub(r'(?i)(patient (presents with|has|had|is|was|reports?|complains? of|experiencing)|symptoms? (suggestive|indicative) of|possible|probable|likely|suspected|consistent with|concerning for|history of|evidence of|assessment:?|findings?:?)', '', raw)
    # Split on commas, semicolons, 'including', 'such as', 'and'
    parts = re.split(r'[,;]\s*|\s+including\s+|\s+such as\s+|\s+and\s+', cleaned)
    results = []
    for p in parts:
        p = re.sub(r'(?i)^(including|such as|like|with)\s+', '', p.strip().strip('.').strip(':').strip())
        # Must be short, no colons (skip template text), and meaningful
        if 3 < len(p) < 50 and ':' not in p:
            results.append(p.lower())
    return results

def get_analytics() -> AnalyticsSummary:
    """Compute dashboard analytics from all visits."""
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM visits").fetchone()["cnt"]

        all_conditions = []
        all_medications = []

        # Extract conditions and medications from clinician notes
        cn_rows = conn.execute("SELECT clinician_note_json FROM visits WHERE clinician_note_json IS NOT NULL").fetchall()
        for row in cn_rows:
            try:
                cn = json.loads(row["clinician_note_json"])
                soap = cn.get("soap_note", {})
                assessment = soap.get("assessment", {})
                for f in assessment.get("findings", []):
                    all_conditions.extend(_clean_condition(f))
                plan = soap.get("plan", {})
                all_medications.extend(plan.get("findings", []))
            except (json.JSONDecodeError, TypeError):
                pass

        # Count conditions and medications
        cond_counts = {}
        for c in all_conditions:
            cond_counts[c] = cond_counts.get(c, 0) + 1
        med_counts = {}
        for m in all_medications:
            med_counts[m] = med_counts.get(m, 0) + 1

        top_conditions = sorted(cond_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_medications = sorted(med_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Visits over time (by month)
        time_rows = conn.execute(
            """SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as cnt
               FROM visits GROUP BY month ORDER BY month"""
        ).fetchall()

        # Get feedback rates
        fb = get_feedback_analytics()
        boosted = get_boosted_keywords(min_score=0.0)
        top_kw = [
            {"keyword": kw.keyword, "positive_count": kw.positive_count, "negative_count": kw.negative_count, "boost_score": kw.boost_score}
            for kw in boosted[:10]
        ]

        return AnalyticsSummary(
            total_visits=total,
            risk_distribution={"low": 0, "medium": 0, "high": 0},
            top_conditions=[{"condition": c, "count": n} for c, n in top_conditions],
            top_medications=[{"medication": m, "count": n} for m, n in top_medications],
            red_flag_frequency={},
            visits_over_time=[{"date": r["month"], "count": r["cnt"]} for r in time_rows],
            avg_risk_score=0.0,
            extraction_accuracy_rate=fb.extraction_accuracy_rate,
            literature_relevance_rate=fb.literature_relevance_rate,
            top_boosted_keywords=top_kw,
        )
    finally:
        conn.close()
