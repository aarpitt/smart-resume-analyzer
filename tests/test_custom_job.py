"""
Automated Test Suite for Custom Job Description Analysis.
Tests:
1. Predefined role regression protection
2. Custom technical role compatibility (e.g. VLSI / Full Stack)
3. Custom non-technical professions (Mechanical Engineer, Project Manager, Financial Analyst)
4. Verification depth (Verified in Experience vs Mentioned in Skills)
5. Weight formula reallocation (60/20/20 vs 80/20 when preferred competencies are empty)
6. Validation checks (short JD < 30 words, missing title)
7. Fallback extraction when API is unavailable or encounters error
8. End-to-end route, dashboard rendering, and database persistence
"""

import io
import os
import html as html_lib
import pytest
from app import create_app
from app.models import db, AnalysisRecord
from app.ats_analyzer import ATSAnalyzer
from app.custom_job_analyzer import CustomJobAnalyzer
from app.scoring import ResumeScorer
from app.feedback import FeedbackGenerator
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


# =========================================================================
# Unit Tests: CustomJobAnalyzer
# =========================================================================

def test_custom_job_rule_based_fallback():
    """Verify deterministic rule-based requirement extraction without Groq."""
    analyzer = CustomJobAnalyzer(api_key=None)
    job_title = "Mechanical Engineer"
    job_description = (
        "We are looking for an experienced Mechanical Engineer to lead thermal systems design.\n"
        "Requirements:\n"
        "- SolidWorks 3D CAD modeling and design for manufacturing (DFM)\n"
        "- Finite Element Analysis (FEA) using ANSYS\n"
        "- Geometric Dimensioning and Tolerancing (GD&T)\n"
        "- 3+ years experience in product engineering\n"
        "- Bachelor's degree in Mechanical Engineering\n"
        "Preferred:\n"
        "- Experience with MATLAB scripting\n"
        "- Six Sigma Green Belt certification\n"
        "Responsibilities:\n"
        "- Execute finite element structural and thermal simulations\n"
        "- Generate engineering drawings and manufacturing specifications"
    )

    reqs = analyzer._extract_via_rules(job_title, job_description)
    assert len(reqs["required_competencies"]) >= 2
    assert len(reqs["preferred_competencies"]) >= 1
    assert len(reqs["experience_requirements"]) >= 1
    assert len(reqs["educational_requirements"]) >= 1
    assert len(reqs["key_responsibilities"]) >= 1


def test_custom_job_api_failure_graceful_fallback():
    """
    Verify that an invalid Groq API key or network error does not crash analysis,
    but instead falls back seamlessly to rule-based extraction with is_fallback=True.
    """
    analyzer = CustomJobAnalyzer(api_key="gsk_invalid_fake_key_123456789")
    job_title = "Operations Director"
    job_description = (
        "Seeking an Operations Director to lead company-wide supply chain optimization.\n"
        "Requirements:\n"
        "- Supply Chain Management and logistics planning\n"
        "- Vendor negotiations and contract management\n"
        "- Lean Manufacturing and process optimization\n"
        "Preferred:\n"
        "- ERP system implementation (SAP)\n"
        "Responsibilities:\n"
        "- Oversee plant operational metrics and quarterly efficiency goals"
    )

    resume_text = (
        "Executive with 10 years experience in Supply Chain Management and logistics planning.\n"
        "Skills: Supply Chain Management, Vendor Negotiations, Lean Manufacturing, SAP\n"
        "Experience: Managed vendor negotiations and contracts. Directed Lean Manufacturing initiatives."
    )
    sections = {
        "skills": "Supply Chain Management, Vendor Negotiations, Lean Manufacturing, SAP",
        "experience": "Managed vendor negotiations and contracts. Directed Lean Manufacturing initiatives.",
        "education": "BS in Industrial Engineering"
    }

    result = analyzer.analyze_custom_compatibility(
        resume_text=resume_text,
        resume_sections=sections,
        job_title=job_title,
        job_description=job_description
    )

    assert result["is_custom_job"] is True
    assert result["is_fallback"] is True
    assert result["ats_score"] > 0
    assert len(result["matched_required_skills"]) >= 1


def test_competency_verification_depth():
    """
    Verify distinction between competencies verified in Experience/Projects (1.0 weight)
    and competencies mentioned only in Skills inventory (0.75 weight).
    """
    analyzer = CustomJobAnalyzer(api_key=None)
    resume_text = (
        "John Doe\n"
        "Skills: Python, Docker, Kubernetes, AWS\n"
        "Experience:\n"
        "Software Engineer at Acme Corp\n"
        "- Architected backend microservices in Python with high availability\n"
        "- Deployed distributed clusters on AWS infrastructure\n"
        "Education: BS in Computer Science"
    )
    sections = {
        "skills": "Python, Docker, Kubernetes, AWS",
        "experience": "Software Engineer at Acme Corp. Architected backend microservices in Python. Deployed on AWS.",
        "projects": "",
        "education": "BS in Computer Science"
    }

    # Python is verified in Experience
    matched_py, level_py = analyzer._check_competency_match("Python", resume_text, sections)
    assert matched_py is True
    assert "Verified" in level_py

    # Docker is only mentioned in Skills
    matched_doc, level_doc = analyzer._check_competency_match("Docker", resume_text, sections)
    assert matched_doc is True
    assert "Mentioned" in level_doc

    # Go is missing entirely
    matched_go, level_go = analyzer._check_competency_match("Go", resume_text, sections)
    assert matched_go is False
    assert level_go == "Missing"


def test_formula_weight_reallocation_when_preferred_is_empty():
    """
    When the job description has no preferred competencies, the formula must
    reallocate the 20% preferred weight into required competencies (80% / 20% TF-IDF)
    rather than penalizing the candidate with 0 for preferred.
    """
    analyzer = CustomJobAnalyzer(api_key=None)
    resume_text = (
        "Project Manager with 6 years experience in agile delivery and scrum.\n"
        "Experience: Led cross-functional teams using Agile methodology, stakeholder management, and budget oversight.\n"
        "Skills: Agile, Scrum, Risk Management, Stakeholder Management, Budgeting"
    )
    sections = {
        "skills": "Agile, Scrum, Risk Management, Stakeholder Management, Budgeting",
        "experience": "Led cross-functional teams using Agile methodology, stakeholder management, and budget oversight.",
        "education": "B.A. Business Administration"
    }

    # Job description with NO preferred competencies
    jd_no_pref = (
        "Project Manager opening.\n"
        "Requirements:\n"
        "- Agile project management\n"
        "- Stakeholder management\n"
        "- Budget oversight\n"
        "- Risk management\n"
        "Responsibilities:\n"
        "- Deliver enterprise technology projects on time and within scope"
    )

    result = analyzer.analyze_custom_compatibility(
        resume_text=resume_text,
        resume_sections=sections,
        job_title="Project Manager",
        job_description=jd_no_pref
    )

    assert result["is_custom_job"] is True
    assert result["recommended_skills_count"] == 0
    assert result["weights"]["required_weight"] == 80
    assert result["weights"]["recommended_weight"] == 0
    assert result["weights"]["tfidf_weight"] == 20
    assert result["ats_score"] > 60


def test_role_neutral_project_manager():
    """
    Verify that non-technical professions (e.g. Project Manager) are assessed
    on their domain competencies without penalizing for lack of programming skills.
    """
    ats_analyzer = ATSAnalyzer()
    pm_resume = (
        "Jane Doe, PMP\n"
        "Professional Summary: Accomplished Senior Project Manager with 8+ years leading enterprise transformations.\n"
        "Core Competencies: PMP, Agile, Scrum, Risk Management, Risk Mitigation, Stakeholder Engagement, Budget Management, JIRA, Confluence\n"
        "Professional Experience:\n"
        "Senior Project Manager at Global Logistics Corp (2019 - Present)\n"
        "- Directed 14 cross-functional teams executing $10M enterprise supply chain programs using Agile and Scrum frameworks\n"
        "- Managed executive stakeholder engagement across VP and C-level leaders with weekly executive reporting dashboards\n"
        "- Established proactive risk mitigation protocols reducing project schedule deviations by 30%\n"
        "- Controlled $10M project budget management and vendor resource allocations with zero cost overruns\n"
        "- Maintained agile backlogs in JIRA and comprehensive project governance documentation in Confluence\n"
        "Education: Master of Business Administration (MBA)"
    )
    sections = {
        "skills": "PMP, Agile, Scrum, Risk Management, Risk Mitigation, Stakeholder Engagement, Budget Management, JIRA, Confluence",
        "experience": "Directed 14 cross-functional teams executing $10M enterprise programs using Agile and Scrum. Managed executive stakeholder engagement with weekly executive reporting. Established risk mitigation protocols. Controlled $10M budget management. Maintained JIRA and Confluence.",
        "education": "Master of Business Administration (MBA)"
    }
    pm_jd = (
        "Senior Project Manager sought for organizational transformation and enterprise program delivery.\n"
        "Requirements:\n"
        "- PMP certification or formal agile delivery credential\n"
        "- Agile and Scrum team leadership experience\n"
        "- Proven track record in stakeholder engagement and executive reporting\n"
        "- Budget management and risk mitigation expertise\n"
        "Preferred:\n"
        "- JIRA and Confluence fluency\n"
        "Responsibilities:\n"
        "- Lead enterprise workstreams and ensure on-time milestone governance\n"
        "- Facilitate sprint ceremonies and present quarterly progress to steering committees"
    )

    res = ats_analyzer.analyze_custom_job(
        resume_text=pm_resume,
        resume_sections=sections,
        job_title="Senior Project Manager",
        job_description=pm_jd
    )

    assert res["is_custom_job"] is True
    assert res["ats_score"] >= 65
    assert len(res["matched_required_skills"]) >= 2
    # Should not demand Python or React
    assert "Python" not in res["missing_required_skills"]
    assert "React" not in res["missing_required_skills"]


def test_role_neutral_mechanical_engineer():
    """
    Verify that an engineering profession (e.g. Mechanical Engineer)
    is evaluated on domain mechanical skills (CAD, FEA, GD&T, DFM).
    """
    ats_analyzer = ATSAnalyzer()
    mech_resume = (
        "Carlos Mendez, Lead Mechanical Engineer\n"
        "Skills: SolidWorks, GD&T, Finite Element Analysis, AutoCAD, Thermal Modeling, DFM\n"
        "Experience:\n"
        "Mechanical Design Engineer at AeroSystems (2019 - Present)\n"
        "- Developed precision aerospace brackets using SolidWorks and GD&T standards\n"
        "- Performed Finite Element Analysis (FEA) to validate structural integrity\n"
        "- Led Design for Manufacturing (DFM) reviews with machining vendors\n"
        "Education: B.S. in Mechanical Engineering"
    )
    sections = {
        "skills": "SolidWorks, GD&T, Finite Element Analysis, AutoCAD, Thermal Modeling, DFM",
        "experience": "Developed brackets using SolidWorks and GD&T. Performed Finite Element Analysis (FEA). Led DFM reviews.",
        "education": "B.S. in Mechanical Engineering"
    }
    mech_jd = (
        "Seeking an experienced Mechanical Engineer for mechanical hardware design.\n"
        "Requirements:\n"
        "- SolidWorks 3D mechanical modeling expertise\n"
        "- Applied knowledge of GD&T ASME Y14.5 standards\n"
        "- Finite Element Analysis (FEA) experience\n"
        "Preferred:\n"
        "- AutoCAD 2D drafting\n"
        "Responsibilities:\n"
        "- Create production drawings and validate structural tolerances"
    )

    res = ats_analyzer.analyze_custom_job(
        resume_text=mech_resume,
        resume_sections=sections,
        job_title="Mechanical Engineer",
        job_description=mech_jd
    )

    assert res["is_custom_job"] is True
    assert res["ats_score"] >= 65
    assert len(res["matched_required_skills"]) >= 2


def test_role_neutral_financial_analyst():
    """
    Verify that financial roles are evaluated on modeling, valuation, and analytics.
    """
    ats_analyzer = ATSAnalyzer()
    finance_resume = (
        "Sarah Lin, Senior Financial Analyst\n"
        "Professional Summary: Quantitative Financial Analyst with 6 years experience in corporate valuation.\n"
        "Skills: Financial Modeling, DCF Valuation, Excel, Variance Analysis, Forecasting, Financial Reporting\n"
        "Experience:\n"
        "Financial Analyst at Capital Growth Partners (2020 - Present)\n"
        "- Built discounted cash flow (DCF) valuation models and three-statement financial modeling in Excel\n"
        "- Conducted monthly budget variance analysis and dynamic financial forecasting for executive leadership\n"
        "- Produced executive financial presentations and quarterly operational forecasts\n"
        "Education: B.S. in Finance and Economics"
    )
    sections = {
        "skills": "Financial Modeling, DCF Valuation, Excel, Variance Analysis, Forecasting, Financial Reporting",
        "experience": "Built DCF valuation models and financial modeling in Excel. Conducted budget variance analysis and dynamic forecasting. Produced executive financial presentations.",
        "education": "B.S. in Finance"
    }
    finance_jd = (
        "Financial Analyst position available at premier investment firm.\n"
        "Requirements:\n"
        "- Financial modeling and valuation capabilities\n"
        "- Advanced Excel modeling skills\n"
        "- Experience performing variance analysis and financial forecasting\n"
        "Responsibilities:\n"
        "- Prepare executive financial presentations and quarterly operational forecasts"
    )

    res = ats_analyzer.analyze_custom_job(
        resume_text=finance_resume,
        resume_sections=sections,
        job_title="Financial Analyst",
        job_description=finance_jd
    )

    assert res["is_custom_job"] is True
    assert res["ats_score"] >= 60
    assert len(res["matched_required_skills"]) >= 1


# =========================================================================
# Integration Route Tests: Custom Job Description Workflow
# =========================================================================

def test_route_custom_job_short_description_rejected(client):
    """
    Submitting a custom job description with fewer than 30 words must be
    rejected with a clear flash message without performing analysis.
    """
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Custom Job Analysis",
            "custom_job_title": "Biomedical Engineer",
            "custom_job_description": "We need a biomedical engineer with medical device experience.",  # 8 words
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)

    html = response.data.decode("utf-8")
    assert "minimum 30 words" in html


def test_route_custom_job_missing_title_rejected(client):
    """
    Submitting a custom job without a title must be rejected.
    """
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Custom Job Analysis",
            "custom_job_title": "  ",
            "custom_job_description": (
                "We are seeking a seasoned enterprise system administrator to manage Linux servers, "
                "orchestrate cloud networks, configure active directory services, and monitor security "
                "protocols across all production data centers worldwide on a daily basis."
            ),
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)

    html = response.data.decode("utf-8")
    assert "Target Job Title" in html


def test_route_custom_job_successful_analysis(client, app):
    """
    Upload a resume with Custom Job Analysis and verify:
    - 200 OK on result page
    - 'Custom Analysis' badge rendered
    - Target job title displayed
    - Role-Neutral Disclosure banner rendered
    - Database record saved with custom job title
    """
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    custom_jd = (
        "We are looking for a Senior BI and Analytics Specialist to lead our enterprise reporting division. "
        "The ideal candidate must have extensive expertise in SQL database querying, Tableau dashboard design, "
        "data warehouse modeling, and statistical analysis using Python or R. "
        "Responsibilities include gathering business requirements from executive stakeholders, building "
        "automated ETL pipelines, and delivering executive dashboards on weekly operating performance. "
        "A Bachelor's degree in Computer Science, Data Science, or related quantitative field is required."
    )

    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Custom Job Analysis",
            "custom_job_title": "BI & Analytics Specialist",
            "custom_job_description": custom_jd,
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data")

    assert response.status_code == 302
    location = response.headers.get("Location")
    assert "/result/" in location

    res_page = client.get(location)
    assert res_page.status_code == 200
    html = res_page.data.decode("utf-8")

    # Verify custom job elements on dashboard
    assert "Custom Analysis" in html
    assert "Role-Neutral Disclosure" in html
    assert "ATS Skill Gap Analysis" in html
    assert "Analytics Specialist" in html

    # Verify database record
    analysis_id = location.split("/result/")[1]
    with app.app_context():
        record = AnalysisRecord.query.filter_by(analysis_id=analysis_id).first()
        assert record is not None
        assert record.target_role == "BI & Analytics Specialist"
        assert record.overall_score > 0
        assert record.ats_score > 0


def test_route_predefined_role_regression_protection(client):
    """
    Verify that standard predefined roles (Data Analyst, Web Developer, AI Engineer, Cloud Engineer)
    continue to work seamlessly without regressions.
    """
    pdf_path = os.path.join(SAMPLES_DIR, "sample_data_analyst.pdf")
    with open(pdf_path, "rb") as f:
        data = {
            "target_role": "Data Analyst",
            "resume_file": (f, "sample_data_analyst.pdf")
        }
        response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Data Analyst" in html
    assert "ATS Skill Gap Analysis" in html
    # Predefined role does NOT have Custom Analysis badge
    assert "Custom Analysis" not in html


# =========================================================================
# Regression Tests: Issue Fixes for Custom Role Matching, Scoring, & Feedback
# =========================================================================

def test_equivalent_terminology_jira_and_agile_matching():
    """
    ISSUE 3 FIX: Verify equivalent terminology and umbrella term resolution.
    - 'Project Management Tools' matches if resume contains Jira or Trello.
    - 'Agile Methodologies' matches if resume contains Agile, Scrum, or Kanban.
    - Credit is NOT awarded when evidence is missing.
    """
    analyzer = CustomJobAnalyzer(api_key=None)

    # 1. Jira in experience -> Verified in Experience
    matched_jira, level_jira = analyzer._check_competency_match(
        competency="Project Management Tools",
        resume_text="Experience: Spearheaded sprint delivery using Jira to coordinate tasks.",
        sections={"experience": "Spearheaded sprint delivery using Jira to coordinate tasks."}
    )
    assert matched_jira is True
    assert "Verified" in level_jira

    # 2. Trello in skills -> Mentioned in Skills
    matched_trello, level_trello = analyzer._check_competency_match(
        competency="Project Management Tools",
        resume_text="Skills: Trello, Excel, Budgeting",
        sections={"skills": "Trello, Excel, Budgeting", "experience": ""}
    )
    assert matched_trello is True
    assert "Mentioned" in level_trello

    # 3. Agile in experience -> Verified in Experience
    matched_agile, level_agile = analyzer._check_competency_match(
        competency="Agile Methodologies",
        resume_text="Experience: Led cross-functional teams in an Agile Scrum environment.",
        sections={"experience": "Led cross-functional teams in an Agile Scrum environment."}
    )
    assert matched_agile is True
    assert "Verified" in level_agile

    # 4. Scrum in skills -> Mentioned in Skills
    matched_scrum, level_scrum = analyzer._check_competency_match(
        competency="Agile Methodologies",
        resume_text="Skills: Scrum Master, Risk Management",
        sections={"skills": "Scrum Master, Risk Management", "experience": ""}
    )
    assert matched_scrum is True
    assert "Mentioned" in level_scrum

    # 5. Missing when no equivalent tool or methodology is present
    matched_none, level_none = analyzer._check_competency_match(
        competency="Project Management Tools",
        resume_text="Carlos is a CAD designer who uses SolidWorks and GD&T for mechanical parts.",
        sections={"experience": "CAD design in SolidWorks with GD&T."}
    )
    assert matched_none is False
    assert level_none == "Missing"


def test_pm_scoring_not_penalized_for_missing_github_or_programming():
    """
    ISSUE 2 FIX: Verify profession-neutral scoring for non-technical roles.
    - LinkedIn alone gets full contact points without GitHub deduction.
    - Skills section displays 'Professional Competencies' and does not require DevOps/programming tools.
    - 100-point structure remains fully preserved.
    """
    scorer = ResumeScorer()
    pm_parsed = {
        "raw_text": (
            "Jane Doe, PMP\nEmail: jane.doe@example.com\nPhone: (555) 234-5678\n"
            "LinkedIn: https://linkedin.com/in/janedoe-pm\n"
            "Education: Master of Business Administration (MBA), University of Chicago, 2020\n"
            "Experience:\nSenior Project Manager at Acme Corp (2020 - Present)\n"
            "Directed 12 cross-functional teams executing $8M enterprise delivery using Agile and Scrum.\n"
            "Managed stakeholder alignment across executive leadership.\n"
            "Projects: Global ERP Migration\n"
            "Managed $5M budget and 25 stakeholders, delivering project 2 weeks ahead of schedule.\n"
            "Skills: PMP, Agile, Scrum, Risk Mitigation, Budget Management, JIRA, Trello, Confluence"
        ),
        "contact_info": {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "(555) 234-5678",
            "linkedin": "https://linkedin.com/in/janedoe-pm"
        },
        "sections": {
            "education": "Master of Business Administration (MBA), University of Chicago, 2020",
            "experience": "Senior Project Manager at Acme Corp. Directed 12 cross-functional teams executing $8M enterprise delivery using Agile and Scrum. Managed stakeholder alignment across executive leadership.",
            "projects": "Global ERP Migration. Managed $5M budget and 25 stakeholders, delivering project 2 weeks ahead of schedule.",
            "skills": "PMP, Agile, Scrum, Risk Mitigation, Budget Management, JIRA, Trello, Confluence"
        },
        "detected_sections": ["contact", "education", "experience", "projects", "skills"],
        "word_count": 350
    }

    custom_ats_data = {
        "is_custom_job": True,
        "target_role": "Senior Project Manager",
        "required_match_percentage": 100.0,
        "required_matched_count": 5,
        "required_skills_count": 5,
        "matched_required_skills": ["Project Management", "Agile", "Budget Management", "Risk Mitigation", "Stakeholder Alignment"]
    }

    scoring = scorer.score_resume(
        pm_parsed,
        extracted_skills=custom_ats_data["matched_required_skills"],
        is_custom_job=True,
        target_role="Senior Project Manager",
        custom_ats_data=custom_ats_data
    )

    # 1. Contact section: full 15 pts, no GitHub deduction
    contact_bd = scoring["breakdown"]["contact_info"]
    assert contact_bd["score"] == 15
    for deduction in contact_bd["deductions"]:
        assert "github" not in deduction.lower()

    # 2. Skills section: title is Professional Competencies, full 20 pts
    skills_bd = scoring["breakdown"]["skills"]
    assert skills_bd["title"] == "Professional Competencies"
    assert skills_bd["score"] == 20
    for deduction in skills_bd["deductions"]:
        assert "devops" not in deduction.lower()
        assert "programming" not in deduction.lower()
        assert "database" not in deduction.lower()

    # 3. Overall score is competitive (>= 70) and free of technical deductions
    assert scoring["overall_score"] >= 70
    assert scoring["grade"] in ["A", "B"]


def test_pm_feedback_excludes_irrelevant_tech_and_remains_role_aware():
    """
    ISSUE 1 FIX: Verify recommendations for a Project Manager contain role-aware advice
    and do not recommend irrelevant technical stacks (Docker, Kubernetes, SQL, Python, GitHub).
    """
    generator = FeedbackGenerator()
    parsed_data = {
        "contact_info": {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "555-0192",
            "linkedin": "https://linkedin.com/in/janedoe"
        },
        "detected_sections": ["contact", "education", "experience", "projects", "skills"],
        "word_count": 360
    }
    scoring_result = {
        "overall_score": 86,
        "grade": "A",
        "tier": "Strong Profile",
        "breakdown": {}
    }
    ats_result = {
        "is_custom_job": True,
        "target_role": "Senior Project Manager",
        "missing_required_skills": ["Risk Assessment"],
        "matched_required_skills": ["Agile Methodologies", "Stakeholder Management", "Budget Oversight"],
        "missing_recommended_skills": ["Vendor Negotiations"],
        "key_responsibilities": ["Lead milestone governance and quarterly budget reporting"]
    }

    # Test Rule-Based Fallback
    fallback_recs = generator.generate_rule_based_recommendations(parsed_data, scoring_result, ats_result)
    assert len(fallback_recs) >= 1

    for rec in fallback_recs:
        rec_content = (rec["title"] + " " + rec["action"] + " " + rec["evidence"]).lower()
        assert "docker" not in rec_content
        assert "kubernetes" not in rec_content
        assert "github" not in rec_content
        assert "sql" not in rec_content
        assert "devops" not in rec_content

    # Core gap should be managerial (Risk Assessment)
    assert any("Risk Assessment" in r["title"] or "Risk Assessment" in r["evidence"] for r in fallback_recs)


def test_groq_failure_fallback_remains_role_aware():
    """
    Verify that forcing fallback produces role-aware recommendations
    without defaulting to generic technical recruiter feedback.
    """
    generator = FeedbackGenerator(api_key="gsk_invalid_test_key")
    parsed_data = {
        "contact_info": {
            "name": "Michael Scott",
            "email": "mscott@dundermifflin.com",
            "phone": "555-0100",
            "linkedin": "https://linkedin.com/in/mscott"
        },
        "detected_sections": ["contact", "experience", "skills"],
        "word_count": 300
    }
    scoring_result = {
        "overall_score": 75,
        "grade": "B",
        "tier": "Competitive Profile",
        "breakdown": {
            "projects": {"score": 0, "deductions": ["Missing dedicated Projects section"]}
        }
    }
    ats_result = {
        "is_custom_job": True,
        "target_role": "Regional Operations Manager",
        "missing_required_skills": ["P&L Management"],
        "matched_required_skills": ["Team Leadership", "Sales Strategy"],
        "missing_recommended_skills": [],
        "key_responsibilities": ["Oversee branch operations and quarterly revenue targets"]
    }

    recs = generator.generate_recommendations(parsed_data, scoring_result, ats_result, force_fallback=True)
    assert len(recs) >= 1

    # Verify no software tech recommendations
    for r in recs:
        text = (r["title"] + " " + r["action"]).lower()
        assert "github" not in text
        assert "docker" not in text
        assert "tech stack" not in text

    # Missing core competency P&L Management should be recommended
    assert any("P&L Management" in r["title"] or "P&L Management" in r["evidence"] for r in recs)


def test_feedback_sanitizer_removes_invented_numerical_achievements():
    """
    Verify that recommendations never present invented numerical metrics
    (e.g., '$1.2M project budget' or '15% improvement') as facts or examples,
    and instead guide candidates to incorporate their actual, verifiable metrics.
    """
    generator = FeedbackGenerator()

    # 1. Test parenthetical and illustrative metric sanitization
    raw_samples = [
        "Optimize budget allocations (e.g., forecasted $1.2M budget and achieved 5% cost savings).",
        "Quantify project outcomes (e.g., delivered 15% improvement in sprint velocity).",
        "Demonstrate portfolio oversight, such as managing a $2.5M capital budget, to show seniority."
    ]

    for raw in raw_samples:
        sanitized = generator.sanitize_invented_metrics(raw)
        assert "$1.2M" not in sanitized
        assert "15%" not in sanitized
        assert "$2.5M" not in sanitized
        assert "actual, verifiable metrics" in sanitized

    # 2. Test rule-based impact recommendations advise verifiable metrics without hardcoded numbers
    parsed_data = {
        "contact_info": {"email": "test@example.com", "phone": "1234567890"},
        "detected_sections": ["contact", "experience", "skills"],
        "word_count": 350
    }
    scoring_result = {
        "overall_score": 75,
        "grade": "B",
        "tier": "Competitive Profile",
        "breakdown": {
            "structure_impact": {
                "score": 10,
                "deductions": ["Descriptions lack quantifiable metrics and outcomes."]
            }
        }
    }
    ats_result = {
        "is_custom_job": True,
        "target_role": "Project Manager",
        "missing_required_skills": [],
        "matched_required_skills": ["Agile"],
        "missing_recommended_skills": []
    }
    recs = generator.generate_rule_based_recommendations(parsed_data, scoring_result, ats_result)
    impact_recs = [r for r in recs if r["category"] == "Impact & Metrics"]
    assert len(impact_recs) >= 1
    for r in impact_recs:
        assert "35%" not in r["action"]
        assert "actual, verifiable metrics" in r["action"]


def test_score_explanation_distinguishes_general_competencies_from_job_compatibility():
    """
    Verify that general Professional Competencies scoring is explained separately
    from job-specific competency coverage, clarifying why general resume quality
    can be high while job compatibility is moderate or low.
    """
    scorer = ResumeScorer()
    pm_parsed = {
        "raw_text": "Experienced professional with broad skills.",
        "contact_info": {"email": "pm@example.com", "phone": "555-0100", "linkedin": "linkedin.com/in/pm"},
        "sections": {
            "skills": "Budgeting, Risk Management, Agile, Scrum, JIRA, Trello, Leadership, Vendor Management, Scheduling, Reporting"
        },
        "detected_sections": ["contact", "education", "experience", "projects", "skills"],
        "word_count": 400
    }

    # Candidate has 10 general competencies (broad inventory), but only matches 1 of 4 required job competencies
    custom_ats_data = {
        "is_custom_job": True,
        "target_role": "Specialized Healthcare PM",
        "required_match_percentage": 25.0,
        "required_matched_count": 1,
        "required_skills_count": 4,
        "matched_required_skills": ["Leadership"]
    }

    scoring = scorer.score_resume(
        pm_parsed,
        extracted_skills=["Leadership"],
        is_custom_job=True,
        target_role="Specialized Healthcare PM",
        custom_ats_data=custom_ats_data
    )

    skills_bd = scoring["breakdown"]["skills"]
    assert skills_bd["title"] == "Professional Competencies"
    # General competency inventory is recognized (high score due to broad inventory)
    assert skills_bd["score"] >= 16

    # Explanation in reasons must explicitly clarify that it measures general breadth separate from job keyword matching
    explanation = " ".join(skills_bd["reasons"])
    assert "separate from specific target job keyword coverage" in explanation or "general professional breadth" in explanation


