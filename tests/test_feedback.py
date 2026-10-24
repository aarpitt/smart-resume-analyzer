"""
Unit tests for FeedbackGenerator module.
Verifies actionable recommendation generation, evidence linking, and integrity constraints.
"""

import os
import pytest
from app.parser import ResumeParser
from app.scoring import ResumeScorer
from app.ats_analyzer import ATSAnalyzer
from app.feedback import FeedbackGenerator

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


def test_feedback_for_weak_resume():
    weak_path = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")
    parsed = ResumeParser(weak_path).parse()

    ats = ATSAnalyzer()
    all_skills = ats.extract_all_skills(parsed["raw_text"])
    ats_result = ats.analyze_role_compatibility(parsed["raw_text"], "AI Engineer")

    scorer = ResumeScorer()
    scoring_result = scorer.score_resume(parsed, all_skills)

    feedback_gen = FeedbackGenerator()
    recs = feedback_gen.generate_recommendations(parsed, scoring_result, ats_result)

    assert len(recs) > 0

    # Weak resume has no email -> must trigger high priority email recommendation
    categories = [r["category"] for r in recs]
    assert "Contact Details" in categories
    assert any("email" in r["title"].lower() for r in recs)

    # Weak resume has no projects -> must trigger projects recommendation
    assert "Projects" in categories
    assert any("project" in r["title"].lower() for r in recs)

    # Missing core AI skills -> must trigger Role Alignment recommendation
    assert "Role Alignment" in categories

    # Verify that all recommendations contain actionable guidance and evidence
    for rec in recs:
        assert "evidence" in rec and len(rec["evidence"]) > 10
        assert "action" in rec and len(rec["action"]) > 15
        assert rec["severity"] in ["High", "Medium", "Low"]


def test_academic_integrity_no_hallucinated_qualifications():
    """Verify recommendations advise the user on how to showcase authentic work rather than inventing roles."""
    weak_path = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")
    parsed = ResumeParser(weak_path).parse()
    ats_result = ATSAnalyzer().analyze_role_compatibility(parsed["raw_text"], "Cloud Engineer")
    scoring_result = ResumeScorer().score_resume(parsed, [])

    recs = FeedbackGenerator().generate_recommendations(parsed, scoring_result, ats_result)

    for rec in recs:
        action_text = rec["action"].lower()
        # Should not claim "You worked as a Senior Staff Cloud Engineer at Google"
        assert "you worked at" not in action_text
        assert "state that you have 10 years" not in action_text
