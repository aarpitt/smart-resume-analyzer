"""
Resume Scoring Engine.
Calculates a transparent, explainable score out of 100 across 6 foundational resume dimensions.
Note: Scores are illustrative educational heuristics, not definitive claims about actual recruiter decisions.
"""

import json
import os
import re
from typing import Dict, List, Any


class ResumeScorer:
    """
    Evaluates resume completeness and structural quality across six transparent dimensions:
    - Contact Information (15 pts)
    - Education (15 pts)
    - Technical Skills (20 pts)
    - Projects (20 pts)
    - Work Experience (15 pts)
    - Resume Structure & Impact (15 pts)
    """

    DISCLAIMER = (
        "This score is an illustrative heuristic based on standard resume formatting "
        "and ATS best practices. It does not reflect or guarantee actual recruiter decisions."
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

    def score_resume(self, parsed_data: Dict[str, Any], extracted_skills: List[str] = None) -> Dict[str, Any]:
        """
        Calculates the transparent score breakdown across the 6 dimensions.
        """
        raw_text = parsed_data.get("raw_text", "")
        contact_info = parsed_data.get("contact_info", {})
        sections = parsed_data.get("sections", {})
        detected_sections = parsed_data.get("detected_sections", [])
        word_count = parsed_data.get("word_count", 0)
        skills_list = extracted_skills or []

        contact_score = self._score_contact(contact_info)
        education_score = self._score_education(sections.get("education", ""), raw_text)
        skills_score = self._score_skills(sections.get("skills", ""), skills_list)
        projects_score = self._score_projects(sections.get("projects", ""), raw_text)
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

        # Cap between 0 and 100
        total_score = max(0, min(100, round(total_score)))

        # Tier grading
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

    def _score_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
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
            reasons.append("Portfolio / personal website link present.")

        if links_found >= 2:
            score += 4
        elif links_found == 1:
            score += 3
            deductions.append("Only one professional link provided; adding both LinkedIn and GitHub strengthens technical profiles.")
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

        # Dedicated section (6 pts)
        if edu_text.strip():
            score += 6
            reasons.append("Distinct Education section found.")
        else:
            deductions.append("No dedicated 'Education' header detected.")

        # Degree identified (5 pts)
        has_degree = any(re.search(pat, combined) for pat in self.DEGREE_PATTERNS)
        if has_degree:
            score += 5
            reasons.append("Standard academic qualification or degree mentioned (e.g., Bachelor, Master, B.Tech, B.S.).")
        else:
            deductions.append("No standard degree title (B.Tech, B.S., M.S., Bachelor) clearly recognized.")

        # Institution identified (4 pts)
        has_institution = any(re.search(pat, combined) for pat in self.INSTITUTION_PATTERNS)
        if has_institution:
            score += 4
            reasons.append("Educational institution (university/college/institute) detected.")
        else:
            deductions.append("No university or college name clearly identified.")

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

    def _score_skills(self, skills_text: str, skills_list: List[str]) -> Dict[str, Any]:
        max_score = 20
        score = 0
        reasons = []
        deductions = []

        # Skills section presence (6 pts)
        if skills_text.strip():
            score += 6
            reasons.append("Dedicated Technical Skills section detected.")
        else:
            deductions.append("Missing dedicated Skills section.")

        # Skills diversity (up to 14 pts)
        skill_count = len(skills_list)
        if skill_count >= 10:
            score += 14
            reasons.append(f"Strong technical breadth: {skill_count} relevant technical skills identified.")
        elif skill_count >= 6:
            score += 10
            reasons.append(f"Moderate technical breadth: {skill_count} technical skills identified.")
            deductions.append("Could expand skill inventory to showcase additional relevant tools and libraries.")
        elif skill_count >= 3:
            score += 6
            reasons.append(f"Basic skill listing: {skill_count} skills detected.")
            deductions.append("Skill coverage is limited. Add primary programming languages, frameworks, and databases.")
        else:
            score += 2
            deductions.append("Very few recognized technical skills detected in the document.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Technical Skills Section",
            "score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100),
            "status": status,
            "reasons": reasons,
            "deductions": deductions
        }

    def _score_projects(self, proj_text: str, full_text: str) -> Dict[str, Any]:
        max_score = 20
        score = 0
        reasons = []
        deductions = []

        target_text = proj_text if proj_text.strip() else full_text

        # Projects section (6 pts)
        if proj_text.strip():
            score += 6
            reasons.append("Dedicated Projects section present.")
        else:
            deductions.append("Missing dedicated Projects section; crucial for technical and engineering profiles.")

        # Project richness: bullet points / line count (8 pts)
        lines = [line.strip() for line in target_text.splitlines() if len(line.strip()) > 20]
        if len(lines) >= 6:
            score += 8
            reasons.append("Substantial project descriptions with multiple feature points.")
        elif len(lines) >= 3:
            score += 5
            reasons.append("Basic project summaries present.")
            deductions.append("Project descriptions could include more architectural and implementation details.")
        else:
            score += 2
            deductions.append("Very sparse project descriptions. Aim for 2-3 detailed project highlights.")

        # Tech stack / metrics in projects (6 pts)
        has_metrics = bool(re.search(r"\b(\d+[\d,]*%?|\$\d+|\d+\+)\b", target_text))
        has_tech_words = bool(re.search(r"\b(using|built with|implemented|stack|database|api|model)\b", target_text, re.IGNORECASE))

        if has_metrics and has_tech_words:
            score += 6
            reasons.append("Projects highlight implementation technologies and quantitative results.")
        elif has_metrics or has_tech_words:
            score += 4
            reasons.append("Projects mention technical implementation keywords.")
            deductions.append("Incorporate more quantifiable metrics (e.g., % latency reduced, users served, accuracy gained).")
        else:
            score += 1
            deductions.append("Projects lack technical implementation context and quantifiable results.")

        status = self._calc_status(score, max_score)
        return {
            "title": "Projects & Portfolio",
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

        # Experience section presence (5 pts)
        if exp_text.strip():
            score += 5
            reasons.append("Dedicated Professional Experience / Work History section present.")
        else:
            deductions.append("No explicit Experience section found. (If applying as entry-level/fresher, include relevant internships or student leadership).")

        target_text = exp_text if exp_text.strip() else full_text

        # Job role titles detected (5 pts)
        roles_found = [role for role in self.ROLE_PATTERNS if re.search(role, target_text, re.IGNORECASE)]
        if len(roles_found) >= 2:
            score += 5
            reasons.append("Standard professional job titles identified (e.g., Engineer, Developer, Analyst, Intern).")
        elif len(roles_found) == 1:
            score += 3
            reasons.append("At least one professional role title identified.")
        else:
            score += 1
            deductions.append("Standard professional job roles or internship titles not clearly identifiable.")

        # Chronology / Dates (5 pts)
        dates_found = len(re.findall(r"\b(20\d{2}|19\d{2})\b", target_text))
        if dates_found >= 2:
            score += 5
            reasons.append("Chronological date markers indicating tenure and experience timeline.")
        elif dates_found == 1:
            score += 3
            deductions.append("Limited date markers; clarify employment or project tenure.")
        else:
            score += 1
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

        # Section completeness (5 pts)
        core_sections = {"education", "skills", "projects", "experience"}
        matched_core = core_sections.intersection(set(detected_sections))
        if len(matched_core) >= 4:
            score += 5
            reasons.append("All primary structural sections (Education, Skills, Experience, Projects) detected.")
        elif len(matched_core) >= 3:
            score += 4
            reasons.append(f"Most essential sections present ({len(matched_core)} of 4).")
            missing = core_sections - matched_core
            deductions.append(f"Missing core sections: {', '.join(s.title() for s in missing)}.")
        elif len(matched_core) >= 2:
            score += 2
            missing = core_sections - matched_core
            deductions.append(f"Incomplete structure. Missing: {', '.join(s.title() for s in missing)}.")
        else:
            score += 1
            deductions.append("Unstructured format. Standard headers like Education, Skills, and Projects are missing.")

        # Word count balance (4 pts)
        if 350 <= word_count <= 850:
            score += 4
            reasons.append(f"Optimal resume length ({word_count} words; fits concise 1-2 page standard).")
        elif 200 <= word_count < 350:
            score += 3
            reasons.append(f"Concise resume ({word_count} words).")
            deductions.append("Slightly brief; consider adding more project detail or technical achievements.")
        elif word_count > 850:
            score += 2
            deductions.append(f"Resume is on the longer side ({word_count} words). Aim to keep it concise and focused.")
        else:
            score += 1
            deductions.append(f"Resume is very brief ({word_count} words). Expand with substantial content.")

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
        metrics = re.findall(r"\b(\d+[\d,]*%|\$\d+[\d,]*|\d+\+?\s*(users|clients|requests|ms|seconds|x|gb|tb))\b", text_lower)
        if len(metrics) >= 3:
            score += 3
            reasons.append("High quantifiable impact: multiple metrics, percentages, and performance indicators found.")
        elif len(metrics) >= 1:
            score += 2
            reasons.append("Some quantifiable metrics present.")
            deductions.append("Add more quantified outcomes (e.g., 'improved query performance by 35%').")
        else:
            score += 1
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
