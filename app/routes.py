"""
Application Routes and View Controllers.
Handles file uploads, resume parsing, ATS scoring, role matching, feedback generation,
and session-scoped database persistence.
"""

import os
import json
import uuid
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, current_app, abort
)
from werkzeug.utils import secure_filename

from app.models import db, AnalysisRecord
from app.parser import ResumeParser, ParserError
from app.scoring import ResumeScorer
from app.ats_analyzer import ATSAnalyzer
from app.feedback import FeedbackGenerator

main_bp = Blueprint("main", __name__)


def get_or_create_session_id() -> str:
    """Ensures each visitor has a unique session token for privacy isolation."""
    if "user_session_id" not in session:
        session["user_session_id"] = str(uuid.uuid4())
    return session["user_session_id"]


def allowed_file(filename: str) -> bool:
    """Validates allowed file extensions."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@main_bp.route("/")
def index():
    """Landing page with resume upload form and role selector."""
    get_or_create_session_id()
    roles = ATSAnalyzer.SUPPORTED_ROLES
    return render_template("index.html", roles=roles)


@main_bp.route("/analyze", methods=["POST"])
def analyze_resume():
    """
    Handles resume upload, parsing, scoring, ATS matching, and persistence.
    Supports standard form submission and AJAX JSON responses.
    """
    session_id = get_or_create_session_id()

    # 1. Validate Target Role
    target_role = request.form.get("target_role", "").strip()
    if target_role not in ATSAnalyzer.ALL_ROLES:
        flash("Please select a valid target job role from the list.", "danger")
        return redirect(url_for("main.index"))

    is_custom_job = (target_role == ATSAnalyzer.CUSTOM_ROLE_KEY)
    custom_job_title = ""
    custom_job_description = ""

    if is_custom_job:
        custom_job_title = request.form.get("custom_job_title", "").strip()
        custom_job_description = request.form.get("custom_job_description", "").strip()

        if not custom_job_title:
            flash("Please enter a Target Job Title for Custom Job Analysis.", "warning")
            return redirect(url_for("main.index"))

        if not custom_job_description or len(custom_job_description.split()) < 30:
            flash("Please provide a meaningful Job Description (minimum 30 words) for Custom Job Analysis.", "warning")
            return redirect(url_for("main.index"))

        display_role = custom_job_title[:80]
    else:
        display_role = target_role

    # 2. Check for Uploaded File
    if "resume_file" not in request.files:
        flash("No file part provided in upload request.", "danger")
        return redirect(url_for("main.index"))

    file = request.files["resume_file"]
    if file.filename == "":
        flash("No file was selected. Please choose a PDF or DOCX file.", "warning")
        return redirect(url_for("main.index"))

    if not allowed_file(file.filename):
        flash("Invalid file format. Only PDF (.pdf) and Word documents (.docx) are supported.", "danger")
        return redirect(url_for("main.index"))

    # 3. Secure File Handling
    raw_filename = secure_filename(file.filename) or f"resume_{uuid.uuid4().hex[:8]}"
    file_extension = os.path.splitext(raw_filename)[1].lower()
    temp_filename = f"{uuid.uuid4().hex}{file_extension}"
    temp_filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], temp_filename)

    try:
        file.save(temp_filepath)

        # 4. Parse Resume
        parser = ResumeParser(temp_filepath)
        parsed_data = parser.parse()

        # 5. ATS Analysis & NLP Skill Extraction
        ats_analyzer = ATSAnalyzer()
        if is_custom_job:
            ats_result = ats_analyzer.analyze_custom_job(
                resume_text=parsed_data["raw_text"],
                resume_sections=parsed_data["sections"],
                job_title=custom_job_title,
                job_description=custom_job_description,
                api_key=current_app.config.get("GROQ_API_KEY"),
                model=current_app.config.get("GROQ_MODEL")
            )
            all_skills = ats_result.get("all_extracted_skills", [])
        else:
            all_skills = ats_analyzer.extract_all_skills(parsed_data["raw_text"])
            ats_result = ats_analyzer.analyze_role_compatibility(parsed_data["raw_text"], target_role)

        # 6. Heuristic Resume Scoring
        scorer = ResumeScorer()
        scoring_result = scorer.score_resume(
            parsed_data,
            extracted_skills=all_skills,
            is_custom_job=is_custom_job,
            target_role=display_role,
            custom_ats_data=ats_result if is_custom_job else None
        )

        # 7. Actionable Smart Feedback
        feedback_gen = FeedbackGenerator(
            api_key=current_app.config.get("GROQ_API_KEY"),
            model=current_app.config.get("GROQ_MODEL")
        )
        recommendations = feedback_gen.generate_recommendations(
            parsed_data, scoring_result, ats_result
        )

        # 8. Save Analysis Record (avoid permanently storing raw resume text)
        contact_info = parsed_data.get("contact_info", {})
        analysis_id = str(uuid.uuid4())

        record = AnalysisRecord(
            analysis_id=analysis_id,
            session_id=session_id,
            filename=raw_filename,
            file_type=file_extension.replace(".", ""),
            target_role=display_role,
            overall_score=scoring_result["overall_score"],
            ats_score=ats_result["ats_score"],
            grade=scoring_result["grade"],
            tier=scoring_result["tier"],
            candidate_name=contact_info.get("name") or "Candidate",
            candidate_email=contact_info.get("email"),
            word_count=parsed_data.get("word_count", 0),
            breakdown_json=json.dumps(scoring_result),
            ats_data_json=json.dumps(ats_result),
            recommendations_json=json.dumps(recommendations)
        )
        db.session.add(record)
        db.session.commit()

        # Check if client expects JSON (AJAX submission)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return jsonify({
                "success": True,
                "redirect_url": url_for("main.view_result", analysis_id=analysis_id)
            })

        return redirect(url_for("main.view_result", analysis_id=analysis_id))

    except ParserError as pe:
        flash(f"Resume Parsing Error: {str(pe)}", "danger")
        return redirect(url_for("main.index"))
    except Exception as e:
        flash(f"An unexpected error occurred while analyzing the resume: {str(e)}", "danger")
        return redirect(url_for("main.index"))
    finally:
        # Secure cleanup: remove temporary uploaded file immediately
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except OSError:
                pass


@main_bp.route("/result/<analysis_id>")
def view_result(analysis_id: str):
    """
    Renders the modern SaaS dashboard for an individual analysis.
    Enforces session-based privacy.
    """
    session_id = get_or_create_session_id()
    record = AnalysisRecord.query.filter_by(analysis_id=analysis_id).first_or_404()

    # Privacy Protection: Prevent unauthorized users from viewing this record
    if record.session_id != session_id:
        flash("You are not authorized to access this analysis report.", "danger")
        return redirect(url_for("main.index"))

    return render_template(
        "result.html",
        record=record,
        scoring=record.get_breakdown(),
        ats=record.get_ats_data(),
        recommendations=record.get_recommendations()
    )


@main_bp.route("/history")
def history():
    """Lists past analysis reports generated within the current user's session."""
    session_id = get_or_create_session_id()
    records = AnalysisRecord.query.filter_by(session_id=session_id).order_by(
        AnalysisRecord.created_at.desc()
    ).all()
    return render_template("history.html", records=records)


@main_bp.route("/history/clear", methods=["POST"])
def clear_history():
    """Deletes all analysis records for the current user session."""
    session_id = get_or_create_session_id()
    AnalysisRecord.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    flash("Your analysis history has been safely cleared.", "info")
    return redirect(url_for("main.history"))


@main_bp.route("/api/analysis/<analysis_id>")
def api_analysis(analysis_id: str):
    """Provides a RESTful JSON endpoint for analysis data."""
    session_id = get_or_create_session_id()
    record = AnalysisRecord.query.filter_by(analysis_id=analysis_id).first_or_404()

    if record.session_id != session_id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(record.to_dict())


@main_bp.app_errorhandler(413)
def request_entity_too_large(error):
    """Handles upload size exceeding MAX_CONTENT_LENGTH."""
    flash("The uploaded file exceeds the 5MB size limit. Please upload a smaller document.", "danger")
    return redirect(url_for("main.index")), 413


@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500
