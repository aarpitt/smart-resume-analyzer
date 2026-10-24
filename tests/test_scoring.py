"""
Unit tests for ResumeScorer module.
Verifies transparent scoring, breakdown calculation, heuristic disclaimer, and differentiation.
"""

import os
import pytest
from app.parser import ResumeParser
from app.scoring import ResumeScorer
from app.ats_analyzer import ATSAnalyzer

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


@pytest.fixture
def scorer():
    return ResumeScorer()


@pytest.fixture
def ats_analyzer():
    return ATSAnalyzer()


def test_score_strong_ai_resume(scorer, ats_analyzer):
    path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    parsed = ResumeParser(path).parse()
    skills = ats_analyzer.extract_all_skills(parsed["raw_text"])

    result = scorer.score_resume(parsed, skills)

    assert 0 <= result["overall_score"] <= 100
    assert result["overall_score"] >= 80, f"Expected high score for strong resume, got {result['overall_score']}"
    assert result["grade"] in ["A", "B"]
    assert "disclaimer" in result
    assert "heuristic" in result["disclaimer"].lower()

    # Check that all 6 dimensions are present
    breakdown = result["breakdown"]
    dimensions = ["contact_info", "education", "skills", "projects", "experience", "structure_impact"]
    for dim in dimensions:
        assert dim in breakdown
        assert "score" in breakdown[dim]
        assert "max_score" in breakdown[dim]
        assert "status" in breakdown[dim]


def test_score_weak_resume_produces_lower_score(scorer, ats_analyzer):
    path_strong = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    path_weak = os.path.join(SAMPLES_DIR, "sample_weak_resume.docx")

    parsed_strong = ResumeParser(path_strong).parse()
    skills_strong = ats_analyzer.extract_all_skills(parsed_strong["raw_text"])
    score_strong = scorer.score_resume(parsed_strong, skills_strong)["overall_score"]

    parsed_weak = ResumeParser(path_weak).parse()
    skills_weak = ats_analyzer.extract_all_skills(parsed_weak["raw_text"])
    res_weak = scorer.score_resume(parsed_weak, skills_weak)
    score_weak = res_weak["overall_score"]

    # Different resumes produce different scores!
    assert score_strong > score_weak
    assert score_weak < 60, f"Weak resume should score low, got {score_weak}"
    assert res_weak["grade"] in ["C", "D"]

    # Verify deductions for missing email and projects
    breakdown = res_weak["breakdown"]
    assert len(breakdown["contact_info"]["deductions"]) > 0
    assert len(breakdown["projects"]["deductions"]) > 0
