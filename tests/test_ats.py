"""
Unit tests for ATSAnalyzer module.
Verifies skill normalization, alias resolution, role switching impact, and TF-IDF similarity.
"""

import os
import pytest
from app.parser import ResumeParser
from app.ats_analyzer import ATSAnalyzer

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


@pytest.fixture
def ats():
    return ATSAnalyzer()


def test_alias_normalization(ats):
    text = "Proficient in JS, Py, K8s, ML, DL, and Postgres on GCP and AWS."
    skills = ats.extract_all_skills(text)

    # Aliases must map to canonical names
    assert "javascript" in skills
    assert "python" in skills
    assert "kubernetes" in skills
    assert "machine learning" in skills
    assert "deep learning" in skills
    assert "postgresql" in skills
    assert "google cloud platform" in skills
    assert "aws" in skills


def test_role_selection_changes_skill_match_results(ats):
    """
    Core requirement: Verify that selecting different roles against the same resume
    produces distinct, role-aligned match scores and missing skill sets.
    """
    path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    parsed = ResumeParser(path).parse()
    text = parsed["raw_text"]

    # 1. Evaluate against AI Engineer
    ai_result = ats.analyze_role_compatibility(text, "AI Engineer")
    # 2. Evaluate against Cloud Engineer
    cloud_result = ats.analyze_role_compatibility(text, "Cloud Engineer")
    # 3. Evaluate against Web Developer
    web_result = ats.analyze_role_compatibility(text, "Web Developer")

    # The AI resume should score significantly higher for AI Engineer than for Cloud Engineer
    assert ai_result["ats_score"] > cloud_result["ats_score"]
    assert ai_result["required_match_percentage"] > cloud_result["required_match_percentage"]

    # Cloud Engineer should flag missing cloud skills (like Kubernetes, Terraform, Linux)
    missing_for_cloud = [s.lower() for s in cloud_result["missing_required_skills"]]
    assert "terraform" in missing_for_cloud or "kubernetes" in missing_for_cloud or "linux" in missing_for_cloud

    # Web Developer should flag missing web skills (like React, JavaScript, HTML5)
    missing_for_web = [s.lower() for s in web_result["missing_required_skills"]]
    assert "react" in missing_for_web or "javascript" in missing_for_web or "html5" in missing_for_web


def test_tfidf_cosine_similarity(ats):
    ai_path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    parsed = ResumeParser(ai_path).parse()
    text = parsed["raw_text"]

    ai_sim = ats.calculate_tfidf_similarity(text, "AI Engineer")
    cloud_sim = ats.calculate_tfidf_similarity(text, "Cloud Engineer")

    assert 0.0 <= ai_sim <= 1.0
    assert 0.0 <= cloud_sim <= 1.0
    # AI resume semantic content should be more similar to AI benchmark than Cloud benchmark
    assert ai_sim > cloud_sim
