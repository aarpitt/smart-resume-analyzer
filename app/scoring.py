"""
Resume Scoring Engine.
Calculates a transparent, explainable score out of 100 across 6 foundational resume dimensions.
Calibrated to reward meaningful content depth, quantifiable impact, and structural richness
rather than mere presence of section headings.
Note: Scores are illustrative educational heuristics, not definitive claims about actual recruiter decisions.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional


class ResumeScorer:
    """
    Evaluates resume completeness and structural quality across six transparent dimensions:
    - Contact Information (15 pts)
    - Education (15 pts)
    - Technical Skills (20 pts)
    - Projects & Portfolio (20 pts)
    - Work Experience (15 pts)
    - Resume Structure & Impact (15 pts)
    """

    DISCLAIMER = (
        "This score is an illustrative heuristic based on standard resume formatting "
        "and ATS best practices. It evaluates content depth, structure, and keyword relevance. "
        "It does not reflect or guarantee actual recruiter decisions."
    )

    DEGREE_PATTERNS = [
        r"\bb\.?tech\b", r"\bb\.?e\b", r"\bb\.?s\b", r"\bbachelor\b",
        r"\bm\.?tech\b", r"\bm\.?s\b", r"\bmaster\b", r"\bmca\b",
        r"\bph\.?d\b", r"\bdoctorate\b", r"\bdiploma\b", r"\bassociate\b"
    ]

    INSTITUTION_PATTERNS = [
        r"\buniversity\b", r"\bcollege\b", r"\binstitute\b", r"\bschool\b",
        r"\bacademy\b", r"\bcampus\b", r"\biit\b", r"\bnit\b"
    ]

    ROLE_PATTERNS = [
        r"\bengineer\b", r"\bdeveloper\b", r"\banalyst\b", r"\bintern\b",
        r"\bconsultant\b", r"\bspecialist\b", r"\blead\b", r"\bmanager\b",
        r"\barchitect\b", r"\bassociate\b", r"\bresearcher\b", r"\bcoordinator\b"
    ]

    DATE_PATTERNS = [
        r"\b(20\d{2}|19\d{2})\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(20\d{2}|19\d{2})\b",
        r"\bpresent\b", r"\bcurrent\b"
    ]

    def __init__(self, action_verbs_path: str = None):
        if action_verbs_path is None:
            action_verbs_path = os.path.join(
                os.path.dirname(__file__), "data", "action_verbs.json"
            )
        self.action_verbs = self._load_action_verbs(action_verbs_path)

    def _load_action_verbs(self, path: str) -> List[str]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("action_verbs", [])
            except Exception:
                pass
        return ["developed", "built", "designed", "created", "analyzed", "implemented", "optimized"]

    def score_resume(
        self,
        parsed_data: Dict[str, Any],
        extracted_skills: List[str] = None,
        is_custom_job: bool = False,
        target_role: Optional[str] = None,
        custom_ats_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates the transparent score breakdown across the 6 dimensions.
        When is_custom_job=True, evaluations are profession-neutral and adapt to the
        target role requirements rather than demanding software/DevOps libraries.
        """
        raw_text = parsed_data.get("raw_text", "")
        contact_info = parsed_data.get("contact_info", {})
        sections = parsed_data.get("sections", {})
        detected_sections = parsed_data.get("detected_sections", [])
        word_count = parsed_data.get("word_count", 0)
        skills_list = extracted_skills or []

        contact_score = self._score_contact(contact_info, is_custom_job=is_custom_job)
        education_score = self._score_education(sections.get("education", ""), raw_text)
        skills_score = self._score_skills(sections.get("skills", ""), skills_list, is_custom_job=is_custom_job, custom_ats_data=custom_ats_data)
        projects_score = self._score_projects(sections.get("projects", ""), raw_text, is_custom_job=is_custom_job)
        experience_score = self._score_experience(sections.get("experience", ""), raw_text)
        structure_score = self._score_structure(raw_text, detected_sections, word_count)

        total_score = (
            contact_score["score"] +
            education_score["score"] +
            skills_score["score"] +
            projects_score["score"] +
            experience_score["score"] +
            structure_score["score"]
        )

        total_score = max(0, min(100, round(total_score)))

        if total_score >= 85:
            grade = "A"
            tier = "Strong Profile"
        elif total_score >= 70:
            grade = "B"
            tier = "Competitive Profile"
        elif total_score >= 55:
            grade = "C"
            tier = "Moderate Alignment"
        else:
            grade = "D"
            tier = "Needs Significant Improvement"

        return {
            "overall_score": total_score,
            "grade": grade,
            "tier": tier,
            "disclaimer": self.DISCLAIMER,
            "breakdown": {
                "contact_info": contact_score,
                "education": education_score,
                "skills": skills_score,
                "projects": projects_score,
                "experience": experience_score,
                "structure_impact": structure_score
            }
        }

    def _score_contact(self, contact: Dict[str, Any], is_custom_job: bool = False) -> Dict[str, Any]:
        max_score = 15
        score = 0
        reasons = []
        deductions = []

        # Email (5 pts)
        if contact.get("email"):
            score += 5
            reasons.append("Valid professional email address identified.")
        else:
            deductions.append("Missing email address; critical for recruiter contact.")

        # Phone (4 pts)
        if contact.get("phone"):
            score += 4
            reasons.append("Contact phone number detected.")
        else:
            deductions.append("Missing contact phone number.")

        # LinkedIn / GitHub / Portfolio (4 pts)
        links_found = 0
        if contact.get("linkedin"):
            links_found += 1
            reasons.append("LinkedIn profile link present.")
        if contact.get("github"):
            links_found += 1
            reasons.append("GitHub profile link present.")
        if contact.get("portfolio"):
            links_found += 1
            reasons.append("Portfolio link present.")

        if is_custom_job:
            # For custom / profession-neutral roles, LinkedIn or a professional website is standard.
            # GitHub is not required for non-software roles.
            if contact.get("linkedin") or contact.get("portfolio"):
                score += 4
                if not any("LinkedIn" in r or "Portfolio" in r for r in reasons):
                    reasons.append("Professional profile link present.")
            elif links_found >= 1:
                score += 4
            else:
                deductions.append("No professional profile link (such as LinkedIn) detected.")
        else:
            if links_found >= 2:
                score += 4
            elif links_found == 1:
                score += 2
                deductions.append("Only one professional link provided; including both LinkedIn and GitHub strengthens technical profiles.")
            else:
                deductions.append("No professional profiles (LinkedIn or GitHub) detected.")

        # Candidate name (2 pts)
        if contact.get("name") and contact.get("name") != "Candidate":
            score += 2
            reasons.append(f"Candidate name detected: {contact['name']}")
        else:
            score += 1
            deductions.append("Candidate name could not be distinctly identified at the top.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Contact Information",
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_education(self, edu_text: str, full_text: str) -> Dict[str, Any]:
        max_score = 15
        score = 0
        reasons = []
        deductions = []

        combined = (edu_text + " " + full_text).lower()

        # Dedicated section (4 pts)
        if edu_text.strip():
            score += 4
            reasons.append("Distinct Education section found.")
        else:
            deductions.append("No dedicated 'Education' header detected.")

        # Degree identified (4 pts)
        has_degree = any(re.search(pat, combined) for pat in self.DEGREE_PATTERNS)
        if has_degree:
            score += 4
            reasons.append("Standard degree qualification recognized (e.g., Bachelor, Master, B.Tech, B.S.).")
        else:
            deductions.append("No standard degree title clearly recognized.")

        # Institution identified (4 pts)
        has_institution = any(re.search(pat, combined) for pat in self.INSTITUTION_PATTERNS)
        if has_institution:
            score += 4
            reasons.append("Accredited educational institution detected.")
        else:
            deductions.append("No university or college name clearly identified.")

        # Educational depth / dates / field of study (3 pts)
        has_dates = bool(re.search(r"\b(20\d{2}|19\d{2})\b", edu_text if edu_text.strip() else full_text))
        has_field = bool(re.search(r"\b(science|engineering|technology|arts|commerce|mathematics|statistics|computer)\b", combined))
        if has_dates and has_field:
            score += 3
            reasons.append("Complete academic credentials with graduation timeline and field of study.")
        elif has_dates or has_field:
            score += 2
            reasons.append("Basic academic chronology noted.")
        else:
            deductions.append("Incomplete academic entry; add graduation year and academic major/specialization.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Education Details",
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_skills(
        self,
        skills_text: str,
        skills_list: List[str],
        is_custom_job: bool = False,
        custom_ats_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        max_score = 20
        score = 0
        reasons = []
        deductions = []

        title = "Professional Competencies" if is_custom_job else "Technical Skills Section"

        # Skills section presence (4 pts)
        if skills_text.strip():
            score += 4
            reasons.append("Dedicated Competencies / Skills section detected." if is_custom_job else "Dedicated Technical Skills section detected.")
        else:
            deductions.append("Missing dedicated Skills / Competencies section.")

        # Extract items listed in the resume skills section directly (comma, semicolon, bullet separated)
        parsed_section_items = [
            item.strip() for item in re.split(r"[,;•\n\r|/]+", skills_text)
            if 2 <= len(item.strip()) <= 45
        ]
        total_unique_skills = len(set(skills_list + parsed_section_items))

        if is_custom_job:
            # Profession-neutral scoring: evaluates alignment with custom requirements and competency inventory
            req_pct = custom_ats_data.get("required_match_percentage", 0) if custom_ats_data else 0
            req_matched = custom_ats_data.get("required_matched_count", 0) if custom_ats_data else 0

            if (req_pct >= 75 or req_matched >= 4):
                score += 16
                reasons.append(f"Exceptional competency coverage: candidate demonstrated key requirements for this profession.")
            elif total_unique_skills >= 8:
                score += 16
                reasons.append(f"Broad general competency inventory: {total_unique_skills} competencies documented across resume (evaluates overall professional breadth, separate from specific target job keyword coverage).")
            elif (req_pct >= 50 or req_matched >= 3) or total_unique_skills >= 5:
                score += 12
                reasons.append(f"Strong competency coverage matching target job requirements ({total_unique_skills} competencies documented).")
            elif (req_pct >= 25 or req_matched >= 2) or total_unique_skills >= 3:
                score += 8
                reasons.append(f"Moderate competency coverage ({total_unique_skills} competencies detected).")
                deductions.append("Expand competency section to cover additional core methods and qualifications from the job description.")
            else:
                score += 4
                deductions.append("Limited competency coverage matching the supplied job description.")
        else:
            # Standard predefined technical role scoring
            skill_count = len(skills_list)
            if skill_count >= 12:
                score += 16
                reasons.append(f"Exceptional technical breadth: {skill_count} relevant technical skills identified.")
            elif skill_count >= 8:
                score += 12
                reasons.append(f"Strong technical breadth: {skill_count} technical skills identified.")
            elif skill_count >= 5:
                score += 8
                reasons.append(f"Moderate technical breadth: {skill_count} technical skills identified.")
                deductions.append("Expand skill inventory to cover complementary libraries, databases, and DevOps tools.")
            elif skill_count >= 3:
                score += 5
                reasons.append(f"Basic skill coverage: {skill_count} skills detected.")
                deductions.append("Skill coverage is limited. Add primary programming languages, frameworks, and tools.")
            else:
                score += 2
                deductions.append("Very few recognized technical skills detected in the document.")

        status = self._calc_status(score, max_score)
        return {
            "title": title,
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_projects(self, proj_text: str, full_text: str, is_custom_job: bool = False) -> Dict[str, Any]:
        max_score = 20
        score = 0
        reasons = []
        deductions = []

        title = "Projects & Key Initiatives" if is_custom_job else "Projects & Portfolio"

        target_text = proj_text if proj_text.strip() else ""
        proj_words = len(re.findall(r"\b\w+\b", target_text))

        # Projects section header presence (4 pts)
        if proj_text.strip():
            score += 4
            reasons.append("Dedicated Projects / Initiatives section present." if is_custom_job else "Dedicated Projects section present.")
        else:
            deductions.append("Missing dedicated Projects or Initiatives section; valuable for showcasing applied results." if is_custom_job else "Missing dedicated Projects section; crucial for technical and engineering profiles.")

        # Project substance and descriptive richness (up to 10 pts)
        lines = [line.strip() for line in target_text.splitlines() if len(line.strip()) > 30]
        if proj_words >= 90 and len(lines) >= 4:
            score += 10
            reasons.append(f"In-depth project descriptions with {len(lines)} detailed feature/initiative points ({proj_words} words).")
        elif proj_words >= 50 and len(lines) >= 2:
            score += 7
            reasons.append(f"Moderate project summaries present ({proj_words} words).")
            deductions.append("Expand project entries with more context on goals, scope, and strategic decisions." if is_custom_job else "Expand project entries with more architectural context, challenges solved, and design decisions.")
        elif proj_words >= 25:
            score += 4
            reasons.append("Basic project outlines detected.")
            deductions.append("Project descriptions are brief. Elaborate on project scope, methodology, and delivered results." if is_custom_job else "Project descriptions are brief. Elaborate on feature implementation and system architecture.")
        else:
            score += 1
            deductions.append("Sparse or missing project details. Aim for 2-3 substantial project or initiative highlights." if is_custom_job else "Sparse or missing project details. Aim for 2-3 substantial technical project highlights.")

        # Methodology / tech stack keywords and quantifiable metrics (6 pts)
        has_metrics = bool(re.search(r"\b(\d+[\d,]*%?|\$\d+|\d+\+?\s*(users|queries|requests|latency|fps|accuracy|teams|members|clients|projects|budgets|stakeholders|deliverables|cost|savings))\b", target_text, re.IGNORECASE))

        if is_custom_job:
            has_domain_methods = bool(re.search(r"\b(managed|directed|delivered|executed|led|facilitated|budget|schedule|agile|scrum|kanban|pmp|stakeholder|implemented|designed|analyzed|developed|system|process)\b", target_text, re.IGNORECASE))
            if has_metrics and has_domain_methods:
                score += 6
                reasons.append("Projects effectively highlight applied methodologies and quantitative deliverables.")
            elif has_domain_methods:
                score += 4
                reasons.append("Projects describe professional methodologies and leadership.")
                deductions.append("Include quantifiable business outcomes or delivery metrics (e.g., budget scale, schedule efficiency, team size) to substantiate impact.")
            elif has_metrics:
                score += 3
                reasons.append("Projects mention quantitative outcomes.")
                deductions.append("Explicitly state the tools, governance methods, and frameworks utilized for each project.")
            else:
                score += 1
                deductions.append("Projects lack methodology details and quantifiable performance results.")
        else:
            has_tech_words = bool(re.search(r"\b(using|built with|implemented|stack|database|api|model|pipeline|docker|react|pytorch|aws)\b", target_text, re.IGNORECASE))
            if has_metrics and has_tech_words:
                score += 6
                reasons.append("Projects effectively highlight implementation technologies and quantitative results.")
            elif has_tech_words:
                score += 4
                reasons.append("Projects mention technical implementation keywords.")
                deductions.append("Add measurable performance metrics (e.g., % latency reduced, query speedup, model accuracy gained).")
            elif has_metrics:
                score += 3
                reasons.append("Projects mention quantitative results.")
                deductions.append("Explicitly state the technologies, frameworks, and architecture used for each project.")
            else:
                score += 1
                deductions.append("Projects lack technical stack context and quantifiable performance results.")

        status = self._calc_status(score, max_score)
        return {
            "title": title,
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_experience(self, exp_text: str, full_text: str) -> Dict[str, Any]:
        max_score = 15
        score = 0
        reasons = []
        deductions = []

        target_text = exp_text if exp_text.strip() else ""
        exp_words = len(re.findall(r"\b\w+\b", target_text))

        # Experience section presence (3 pts)
        if exp_text.strip():
            score += 3
            reasons.append("Dedicated Professional Experience / Work History section present.")
        else:
            deductions.append("No explicit Experience section found. (Include internships, contracts, or student leadership if entry-level).")

        # Content substance & depth (up to 4 pts)
        exp_lines = [line.strip() for line in target_text.splitlines() if len(line.strip()) > 30]
        if exp_words >= 80 and len(exp_lines) >= 3:
            score += 4
            reasons.append(f"Substantial work history descriptions ({exp_words} words across {len(exp_lines)} accomplishment statements).")
        elif exp_words >= 40:
            score += 2
            reasons.append(f"Basic work history descriptions ({exp_words} words).")
            deductions.append("Deepen work history bullet points with specific responsibilities and business impact.")
        else:
            score += 1
            deductions.append("Work experience section is brief or lacks bulleted accomplishment details.")

        eval_text = exp_text if exp_text.strip() else full_text

        # Job role titles detected (4 pts)
        roles_found = [role for role in self.ROLE_PATTERNS if re.search(role, eval_text, re.IGNORECASE)]
        if len(roles_found) >= 2:
            score += 4
            reasons.append("Clear professional role titles identified (e.g., Engineer, Developer, Analyst).")
        elif len(roles_found) == 1:
            score += 2
            reasons.append("At least one professional role title identified.")
        else:
            deductions.append("Standard professional job roles or internship titles not clearly identifiable.")

        # Chronology / Dates (4 pts)
        dates_found = len(re.findall(r"\b(20\d{2}|19\d{2})\b", eval_text))
        if dates_found >= 2:
            score += 4
            reasons.append("Chronological date markers indicating tenure and professional timeline.")
        elif dates_found == 1:
            score += 2
            deductions.append("Limited date markers; clarify employment or project tenure.")
        else:
            deductions.append("Missing employment date ranges or tenure indicators.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Work Experience",
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_structure(self, full_text: str, detected_sections: List[str], word_count: int) -> Dict[str, Any]:
        max_score = 15
        score = 0
        reasons = []
        deductions = []

        # Section completeness (4 pts)
        core_sections = {"education", "skills", "projects", "experience"}
        matched_core = core_sections.intersection(set(detected_sections))
        if len(matched_core) >= 4:
            score += 4
            reasons.append("All primary structural sections (Education, Skills, Experience, Projects) detected.")
        elif len(matched_core) >= 3:
            score += 3
            reasons.append(f"Most essential sections present ({len(matched_core)} of 4).")
            missing = core_sections - matched_core
            deductions.append(f"Missing core section: {', '.join(s.title() for s in missing)}.")
        elif len(matched_core) >= 2:
            score += 2
            missing = core_sections - matched_core
            deductions.append(f"Incomplete structure. Missing: {', '.join(s.title() for s in missing)}.")
        else:
            score += 1
            deductions.append("Unstructured format. Missing standard resume headings.")

        # Word count & content depth calibration (5 pts)
        # Professional standard: 400 - 800 words
        if 400 <= word_count <= 850:
            score += 5
            reasons.append(f"Optimal resume length and depth ({word_count} words; fits industry standard 1-2 pages).")
        elif 320 <= word_count < 400:
            score += 3
            reasons.append(f"Moderately concise resume ({word_count} words).")
            deductions.append("Slightly brief; expand project implementation details and measurable achievements.")
        elif 200 <= word_count < 320:
            score += 2
            reasons.append(f"Short resume ({word_count} words).")
            deductions.append(f"Document is brief ({word_count} words). Elaborate on technical challenges and impact.")
        elif word_count > 850:
            score += 2
            deductions.append(f"Resume is on the longer side ({word_count} words). Tighten phrasing to maintain recruiter focus.")
        else:
            score += 0
            deductions.append(f"Resume is very brief ({word_count} words; under 200-word threshold). Lacks substantive depth.")

        # Action verbs usage (3 pts)
        text_lower = full_text.lower()
        verbs_found = [v for v in self.action_verbs if re.search(r"\b" + re.escape(v) + r"\b", text_lower)]
        if len(verbs_found) >= 6:
            score += 3
            reasons.append(f"Strong action orientation with {len(verbs_found)} dynamic action verbs.")
        elif len(verbs_found) >= 3:
            score += 2
            reasons.append(f"Moderate action verb usage ({len(verbs_found)} verbs).")
            deductions.append("Begin more bullet points with strong impact verbs (e.g., Architected, Spearheaded, Optimized).")
        else:
            score += 1
            deductions.append("Limited action verbs detected. Passive phrasing reduces recruiter engagement.")

        # Quantified impact (3 pts)
        metrics = re.findall(r"\b(\d+[\d,]*%|\$\d+[\d,]*|\d+\+?\s*(users|clients|requests|ms|seconds|x|gb|tb|accuracy))\b", text_lower)
        if len(metrics) >= 3:
            score += 3
            reasons.append("High quantifiable impact: multiple metrics, percentages, and performance indicators found.")
        elif len(metrics) >= 1:
            score += 2
            reasons.append("Some quantifiable metrics present.")
            deductions.append("Add more quantified outcomes (e.g., 'improved query performance by 35%').")
        else:
            score += 0
            deductions.append("No quantifiable metrics detected. Use numbers, percentages, and metrics to demonstrate impact.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Structure & Impact",
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    @staticmethod
    def _calc_status(score: int, max_score: int) -> str:
        ratio = score / max_score
        if ratio >= 0.8:
            return "Excellent"
        elif ratio >= 0.6:
            return "Good"
        elif ratio >= 0.4:
            return "Needs Improvement"
        return "Critical Attention"
