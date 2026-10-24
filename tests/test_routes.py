"""
Integration and End-to-End Route Tests.
Verifies the complete web application workflow, file uploads, role changes,
result dashboard presentation, session privacy, and error handling.
"""

import io
import os
import pytest
from app import create_app
from app.models import db, AnalysisRecord
from config import TestConfig

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_resumes")


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Smart Resume Analyzer" in html
    assert "Data Analyst" in html
    assert "Web Developer" in html
    assert "AI Engineer" in html
    assert "Cloud Engineer" in html


def test_reject_unsupported_file_extension(client):
    data = {
        "target_role": "Data Analyst",
        "resume_file": (io.BytesIO(b"Hello world resume text"), "resume.txt")
    }
    response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    html = response.data.decode("utf-8")
    assert "Invalid file format" in html


def test_reject_invalid_target_role(client):
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Astronaut",
            "resume_file": (f, "resume.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert "valid target job role" in html


def test_successful_pdf_upload_and_dashboard(client):
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    assert os.path.exists(pdf_path)

    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Data Analyst",
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Check dashboard elements
    assert "Maya Patel" in html
    assert "Data Analyst" in html
    assert "ATS Role Compatibility" in html
    assert "Explainable Score Breakdown" in html
    assert "Personalized Improvement Recommendations" in html
    assert "Educational Heuristic Disclaimer" in html


def test_successful_docx_upload(client):
    docx_path = os.path.join(SAMPLES_DIR, "sample_ai_engineer.docx")
    assert os.path.exists(docx_path)

    with open(docx_path, "rb") as f:
        data = {
            "target_role": "AI Engineer",
            "resume_file": (f, "sample_ai_engineer.docx")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Alex Chen" in html
    assert "AI Engineer" in html


def test_session_privacy_isolation(client, app):
    """
    Ensure one user's analysis is not accessible to another user session.
    """
    # 1. User A uploads a resume
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Data Analyst",
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data")

    # Find the analysis id from redirect URL
    location = response.headers.get("Location")
    analysis_id = location.split("/result/")[1]

    # User A accesses result -> 200 OK
    resp_user_a = client.get(f"/result/{analysis_id}")
    assert resp_user_a.status_code == 200

    # 2. User B in a completely separate session tries to access User A's analysis
    with app.test_client() as client_b:
        resp_user_b = client_b.get(f"/result/{analysis_id}", follow_redirects=True)
        html_b = resp_user_b.data.decode("utf-8")
        # Should be blocked from accessing User A's report
        assert "not authorized to access this analysis report" in html_b


def test_history_and_clear(client):
    # Upload resume
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Data Analyst",
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        client.post("/analyze", data=data, content_type="multipart/form-data")

    # View history
    resp = client.get("/history")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Maya Patel" in html
    assert "Data Analyst" in html

    # Clear history
    clear_resp = client.post("/history/clear", follow_redirects=True)
    clear_html = clear_resp.data.decode("utf-8")
    assert "cleared" in clear_html
    assert "No Analysis Records Yet" in clear_html


def test_api_endpoint(client):
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Data Analyst",
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        resp = client.post("/analyze", data=data, content_type="multipart/form-data")

    analysis_id = resp.headers.get("Location").split("/result/")[1]
    api_resp = client.get(f"/api/analysis/{analysis_id}")
    assert api_resp.status_code == 200
    json_data = api_resp.get_json()

    assert json_data["target_role"] == "Data Analyst"
    assert "overall_score" in json_data
    assert "ats_score" in json_data
    assert "breakdown" in json_data
    assert "recommendations" in json_data
