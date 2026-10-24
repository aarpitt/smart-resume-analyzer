"""
Database Models for SQLite.
Stores analysis metadata and explainable results without permanently persisting raw resume text.
"""

import json
import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AnalysisRecord(db.Model):
    """
    Stores resume evaluation records, isolated by user session.
    """
    __tablename__ = "analysis_records"

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)

    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    target_role = db.Column(db.String(50), nullable=False)

    overall_score = db.Column(db.Integer, nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    tier = db.Column(db.String(50), nullable=False)

    candidate_name = db.Column(db.String(100), default="Candidate")
    candidate_email = db.Column(db.String(120), nullable=True)
    word_count = db.Column(db.Integer, default=0)

    # JSON-encoded analytical results
    breakdown_json = db.Column(db.Text, nullable=False, default="{}")
    ats_data_json = db.Column(db.Text, nullable=False, default="{}")
    recommendations_json = db.Column(db.Text, nullable=False, default="[]")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def get_breakdown(self):
        try:
            return json.loads(self.breakdown_json)
        except Exception:
            return {}

    def get_ats_data(self):
        try:
            return json.loads(self.ats_data_json)
        except Exception:
            return {}

    def get_recommendations(self):
        try:
            return json.loads(self.recommendations_json)
        except Exception:
            return []

    def to_dict(self):
        return {
            "analysis_id": self.analysis_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "target_role": self.target_role,
            "overall_score": self.overall_score,
            "ats_score": self.ats_score,
            "grade": self.grade,
            "tier": self.tier,
            "candidate_name": self.candidate_name,
            "candidate_email": self.candidate_email,
            "word_count": self.word_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "breakdown": self.get_breakdown(),
            "ats_data": self.get_ats_data(),
            "recommendations": self.get_recommendations()
        }
