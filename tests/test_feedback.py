"""
Unit and Integration tests for FeedbackGenerator module.
Verifies rule-based recommendations, Groq Cloud AI LLM feedback,
graceful fallback on API failure, and academic integrity constraints.
"""

import os
import pytest
from app.parser import ResumeParser
from app.scoring import ResumeScorer
from app.ats_analyzer import ATSAnalyzer
from app.feedback import FeedbackGenerator

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


def test_rule_based_feedback_for_weak_resume():
    """Verify rule-based feedback accurately flags missing sections, contact info, and skills."""
    weak_path = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")
    parsed = ResumeParser(weak_path).parse()

    ats = ATSAnalyzer()
    all_skills = ats.extract_all_skills(parsed["raw_text"])
    ats_result = ats.analyze_role_compatibility(parsed["raw_text"], "AI Engineer")

    scorer = ResumeScorer()
    scoring_result = scorer.score_resume(parsed, all_skills)

    feedback_gen = FeedbackGenerator()
    recs = feedback_gen.generate_rule_based_recommendations(parsed, scoring_result, ats_result)

    assert len(recs) > 0

    # Weak resume has no email -> must trigger email recommendation
    categories = [r["category"] for r in recs]
    assert "Contact Details" in categories
    assert any("email" in r["title"].lower() for r in recs)

    # Weak resume has no projects -> must trigger projects recommendation
    assert "Projects" in categories
    assert any("project" in r["title"].lower() for r in recs)

    # Missing core AI skills -> must trigger Role Alignment recommendation
    assert "Role Alignment" in categories

    for rec in recs:
        assert "evidence" in rec and len(rec["evidence"]) > 10
        assert "action" in rec and len(rec["action"]) > 15
        assert rec["severity"] in ["High", "Medium", "Low"]
        assert rec["source"] == "Rule-Based Engine"


def test_groq_ai_feedback_generation():
    """Verify Groq API generates genuine, contextual AI recommendations with schema compliance."""
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        pytest.skip("GROQ_API_KEY not configured in environment")

    path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    parsed = ResumeParser(path).parse()

    ats = ATSAnalyzer()
    all_skills = ats.extract_all_skills(parsed["raw_text"])
    ats_result = ats.analyze_role_compatibility(parsed["raw_text"], "AI Engineer")

    scorer = ResumeScorer()
    scoring_result = scorer.score_resume(parsed, all_skills)

    feedback_gen = FeedbackGenerator(api_key=groq_key)
    recs = feedback_gen.generate_recommendations(parsed, scoring_result, ats_result)

    assert len(recs) >= 2, "Groq should return multiple actionable recommendations"

    for rec in recs:
        assert "title" in rec and len(rec["title"]) > 3
        assert "evidence" in rec and len(rec["evidence"]) > 5
        assert "action" in rec and len(rec["action"]) > 10
        assert rec["severity"] in ["High", "Medium", "Low"]
        assert "source" in rec
        assert "AI (Groq" in rec["source"] or "Rule-Based" in rec["source"]


def test_graceful_fallback_on_api_failure():
    """Verify system falls back seamlessly to rule-based engine when API fails or key is invalid."""
    weak_path = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")
    parsed = ResumeParser(weak_path).parse()

    ats = ATSAnalyzer()
    all_skills = ats.extract_all_skills(parsed["raw_text"])
    ats_result = ats.analyze_role_compatibility(parsed["raw_text"], "AI Engineer")

    scorer = ResumeScorer()
    scoring_result = scorer.score_resume(parsed, all_skills)

    # Intentionally invalid API key to simulate connection / authorization failure
    bad_feedback_gen = FeedbackGenerator(api_key="gsk_invalid_test_key_12345")
    recs = bad_feedback_gen.generate_recommendations(parsed, scoring_result, ats_result)

    # Fallback should succeed and return rule-based recommendations
    assert len(recs) > 0
    assert any(r["source"] == "Rule-Based Engine" for r in recs)
    assert any("email" in r["title"].lower() for r in recs)


def test_academic_integrity_no_hallucinated_qualifications():
    """Verify recommendations advise the user on how to showcase authentic work rather than inventing roles."""
    weak_path = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")
    parsed = ResumeParser(weak_path).parse()
    ats_result = ATSAnalyzer().analyze_role_compatibility(parsed["raw_text"], "Cloud Engineer")
    scoring_result = ResumeScorer().score_resume(parsed, [])

    recs = FeedbackGenerator().generate_rule_based_recommendations(parsed, scoring_result, ats_result)

    for rec in recs:
        action_text = rec["action"].lower()
        assert "you worked at" not in action_text
        assert "state that you have 10 years" not in action_text
