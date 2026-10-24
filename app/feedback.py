"""
Smart Feedback Generator Module.
Generates explainable, evidence-backed recommendations to improve resume competitiveness.
Supports Groq Cloud AI LLM generation with seamless automatic fallback to rule-based analysis.
Strictly adheres to academic integrity: never fabricates experience or qualifications.
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """
    Evaluates scoring deductions and ATS role gap analysis to generate
    prioritized, actionable improvement recommendations with transparent evidence.
    Supports Groq AI enhancement with deterministic rule-based fallback.
    """

    SUPPORTED_CATEGORIES = [
        "Role Alignment",
        "Technical Skills",
        "Projects",
        "Work Experience",
        "Education",
        "Contact Details",
        "Resume Structure",
        "Impact & Metrics"
    ]

    CANDIDATE_MODELS = [
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_MODEL")

    def generate_recommendations(
        self,
        parsed_data: Dict[str, Any],
        scoring_result: Dict[str, Any],
        ats_result: Dict[str, Any],
        force_fallback: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Main entry point. Attempts to use Groq AI for contextual recommendations;
        gracefully falls back to rule-based engine if Groq is unavailable, unconfigured,
        or encounters any network / model errors.
        """
        if self.api_key and not force_fallback:
            try:
                ai_recs = self.generate_groq_recommendations(parsed_data, scoring_result, ats_result)
                if ai_recs and len(ai_recs) >= 2:
                    return ai_recs
            except Exception as e:
                # Log without exposing sensitive credentials
                logger.warning(f"Groq AI feedback unavailable ({type(e).__name__}). Falling back to rule-based analysis.")

        # Fallback to rule-based recommendations
        return self.generate_rule_based_recommendations(parsed_data, scoring_result, ats_result)

    def generate_groq_recommendations(
        self,
        parsed_data: Dict[str, Any],
        scoring_result: Dict[str, Any],
        ats_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calls Groq API to produce structured, personalized recommendations.
        """
        from groq import Groq

        client = Groq(api_key=self.api_key)

        # Build candidate models list with user preference first
        models_to_try = []
        if self.model:
            models_to_try.append(self.model)
        for m in self.CANDIDATE_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        target_role = ats_result.get("target_role", "Software Engineer")
        overall_score = scoring_result.get("overall_score", 0)
        grade = scoring_result.get("grade", "N/A")
        tier = scoring_result.get("tier", "N/A")
        missing_required = ats_result.get("missing_required_skills", [])
        matched_required = ats_result.get("matched_required_skills", [])
        missing_recommended = ats_result.get("missing_recommended_skills", [])
        detected_sections = parsed_data.get("detected_sections", [])
        word_count = parsed_data.get("word_count", 0)
        contact = parsed_data.get("contact_info", {})

        # Extract deductions from scoring
        deductions_summary = []
        for sec_name, sec_data in scoring_result.get("breakdown", {}).items():
            for d in sec_data.get("deductions", []):
                deductions_summary.append(f"{sec_data.get('title')}: {d}")

        system_prompt = (
            "You are a Senior Technical Recruiter and AI Resume Advisor. "
            "Analyze the candidate's automated resume evaluation diagnostics and generate 3 to 5 "
            "high-impact, actionable, and explainable recommendations.\n\n"
            "CRITICAL RULES:\n"
            "1. Output MUST be a valid JSON object with root key 'recommendations' containing a list of objects.\n"
            "2. Each object must have these exact keys:\n"
            "   - 'category': One of ['Role Alignment', 'Technical Skills', 'Projects', 'Work Experience', 'Education', 'Contact Details', 'Resume Structure', 'Impact & Metrics']\n"
            "   - 'severity': Exactly one of ['High', 'Medium', 'Low']\n"
            "   - 'title': Concise actionable title (under 10 words)\n"
            "   - 'evidence': Clear factual summary of what was found or missing in the resume\n"
            "   - 'action': Concrete instruction on how to address this gap.\n"
            "3. ACADEMIC INTEGRITY: Never invent fictional job positions, companies, or falsified accomplishments. "
            "Advise the candidate on how to authentically showcase their real skills, projects, and coursework."
        )

        user_content = (
            f"Candidate Diagnostics:\n"
            f"- Target Role: {target_role}\n"
            f"- Overall Resume Score: {overall_score}/100 (Grade {grade}, {tier})\n"
            f"- Word Count: {word_count}\n"
            f"- Contact Detected: Email={'Yes' if contact.get('email') else 'No'}, "
            f"Phone={'Yes' if contact.get('phone') else 'No'}, "
            f"LinkedIn={'Yes' if contact.get('linkedin') else 'No'}, "
            f"GitHub={'Yes' if contact.get('github') else 'No'}\n"
            f"- Detected Sections: {', '.join(detected_sections) if detected_sections else 'None'}\n"
            f"- Missing Core Skills for {target_role}: {', '.join(missing_required) if missing_required else 'None'}\n"
            f"- Matched Core Skills: {', '.join(matched_required) if matched_required else 'None'}\n"
            f"- Missing Recommended Tools: {', '.join(missing_recommended[:5]) if missing_recommended else 'None'}\n"
            f"- Detected Weaknesses & Deductions:\n" +
            "\n".join(f"  * {d}" for d in deductions_summary[:6])
        )

        last_error = None
        for model_id in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=650,
                    temperature=0.3
                )
                raw_content = response.choices[0].message.content.strip()
                parsed_json = json.loads(raw_content)

                recs_list = parsed_json.get("recommendations", [])
                if isinstance(recs_list, list) and len(recs_list) > 0:
                    cleaned_recs = []
                    for item in recs_list:
                        if isinstance(item, dict) and "title" in item and "action" in item:
                            category = item.get("category", "Role Alignment")
                            severity = item.get("severity", "Medium")
                            if severity not in ["High", "Medium", "Low"]:
                                severity = "Medium"
                            cleaned_recs.append({
                                "category": category,
                                "severity": severity,
                                "title": item.get("title", "Resume Improvement"),
                                "evidence": item.get("evidence", "Identified through ATS structural analysis."),
                                "action": item.get("action", ""),
                                "source": f"AI (Groq: {model_id.split('/')[-1]})"
                            })

                    if cleaned_recs:
                        # Sort by severity: High first, then Medium, then Low
                        severity_order = {"High": 1, "Medium": 2, "Low": 3}
                        cleaned_recs.sort(key=lambda r: severity_order.get(r.get("severity", "Low"), 4))
                        return cleaned_recs
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error

        return []

    def generate_rule_based_recommendations(
        self,
        parsed_data: Dict[str, Any],
        scoring_result: Dict[str, Any],
        ats_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Produces a prioritized list of actionable recommendations with evidence and impact rating
        using deterministic heuristics and NLP gap analysis.
        """
        recommendations: List[Dict[str, Any]] = []

        # 1. Contact Information Recommendations
        contact = parsed_data.get("contact_info", {})
        if not contact.get("email"):
            recommendations.append({
                "category": "Contact Details",
                "severity": "High",
                "title": "Add a Professional Email Address",
                "evidence": "No valid email address was detected in the document header.",
                "action": "Include an active email using a professional name format (e.g., firstname.lastname@example.com) at the top of the resume.",
                "source": "Rule-Based Engine"
            })

        if not contact.get("phone"):
            recommendations.append({
                "category": "Contact Details",
                "severity": "High",
                "title": "Include a Direct Phone Number",
                "evidence": "No standard telephone contact number was identified.",
                "action": "Provide a phone number with country code so recruiters can easily schedule phone screens.",
                "source": "Rule-Based Engine"
            })

        if not contact.get("linkedin") and not contact.get("github"):
            recommendations.append({
                "category": "Contact Details",
                "severity": "Medium",
                "title": "Add Professional Profile Links (LinkedIn / GitHub)",
                "evidence": "Neither a LinkedIn profile URL nor a GitHub repository was detected.",
                "action": "Link to your public LinkedIn profile and GitHub account to provide verification of your background and code samples.",
                "source": "Rule-Based Engine"
            })
        elif not contact.get("github") and ats_result.get("target_role") in ["Web Developer", "AI Engineer", "Cloud Engineer"]:
            recommendations.append({
                "category": "Contact Details",
                "severity": "Medium",
                "title": "Add GitHub / Code Repository Link",
                "evidence": f"A GitHub link was not detected, which is standard for {ats_result.get('target_role')} applicants.",
                "action": "Add a link to your GitHub account showcasing clean repositories, README documentation, and open-source contributions.",
                "source": "Rule-Based Engine"
            })

        # 2. ATS Role-Specific Skills Recommendations
        missing_req = ats_result.get("missing_required_skills", [])
        if missing_req:
            top_missing = missing_req[:4]
            recommendations.append({
                "category": "Role Alignment",
                "severity": "High",
                "title": f"Address Core Skill Gaps for {ats_result.get('target_role')}",
                "evidence": f"Essential required skills for this role are missing from your resume: {', '.join(top_missing)}.",
                "action": f"If you have experience or academic coursework with any of these ({', '.join(top_missing)}), explicitly mention them in your Skills and Projects sections.",
                "source": "Rule-Based Engine"
            })

        missing_rec = ats_result.get("missing_recommended_skills", [])
        if len(missing_rec) >= 4 and not missing_req:
            top_rec = missing_rec[:3]
            recommendations.append({
                "category": "Role Alignment",
                "severity": "Low",
                "title": "Add Secondary Industry Tools to Stand Out",
                "evidence": f"While core skills are present, incorporating complementary tools like {', '.join(top_rec)} will elevate your profile above average applicants.",
                "action": "Highlight familiarity with complementary frameworks, tools, or libraries used in modern team environments.",
                "source": "Rule-Based Engine"
            })

        # 3. Education Recommendations
        edu_score = scoring_result.get("breakdown", {}).get("education", {})
        if "education" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Education",
                "severity": "High",
                "title": "Add a Dedicated Education Section",
                "evidence": "No distinct 'Education' section heading was identified.",
                "action": "Create an 'Education' section listing your degree, major, university/college name, and graduation year.",
                "source": "Rule-Based Engine"
            })
        elif edu_score.get("deductions"):
            recommendations.append({
                "category": "Education",
                "severity": "Medium",
                "title": "Clarify Academic Credentials",
                "evidence": "; ".join(edu_score.get("deductions", [])),
                "action": "Clearly state your degree type (e.g., B.S., B.Tech, Master's) alongside the full institution name and graduation timeline.",
                "source": "Rule-Based Engine"
            })

        # 4. Projects Recommendations
        proj_score = scoring_result.get("breakdown", {}).get("projects", {})
        if "projects" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Projects",
                "severity": "High",
                "title": "Add a Dedicated Projects Section",
                "evidence": "Technical recruiters prioritize practical implementations, but no 'Projects' section was detected.",
                "action": "Add 2-3 substantial projects detailing what you built, the tech stack utilized, your role, and the outcome.",
                "source": "Rule-Based Engine"
            })
        elif proj_score.get("score", 0) < 14:
            recommendations.append({
                "category": "Projects",
                "severity": "Medium",
                "title": "Deepen Project Descriptions with Tech Stack and Impact",
                "evidence": "Existing project entries are brief or lack technical implementation details and results.",
                "action": "Structure each project entry with: Problem statement, Technologies utilized, and Quantifiable results or user impact.",
                "source": "Rule-Based Engine"
            })

        # 5. Experience Recommendations
        exp_score = scoring_result.get("breakdown", {}).get("experience", {})
        if "experience" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Work Experience",
                "severity": "Medium",
                "title": "Add Practical Experience or Relevant Internships",
                "evidence": "No 'Experience' or 'Work History' section was recognized.",
                "action": "If you have prior internships, freelance contracts, research assistantships, or student leadership roles, document them chronologically with responsibilities.",
                "source": "Rule-Based Engine"
            })
        elif exp_score.get("score", 0) < 10:
            recommendations.append({
                "category": "Work Experience",
                "severity": "Medium",
                "title": "Standardize Job Titles and Timeline Dates",
                "evidence": "Job titles or employment date ranges are ambiguous or missing.",
                "action": "Explicitly format each position with: Role Title, Company/Organization Name, Location, and Date Range (e.g., 'May 2023 - Aug 2023').",
                "source": "Rule-Based Engine"
            })

        # 6. Structure, Action Verbs, and Quantified Metrics
        struct_score = scoring_result.get("breakdown", {}).get("structure_impact", {})
        word_count = parsed_data.get("word_count", 0)

        if word_count < 250:
            recommendations.append({
                "category": "Resume Structure",
                "severity": "High",
                "title": "Expand Resume Content",
                "evidence": f"Total document length is only {word_count} words, which appears thin to screening algorithms.",
                "action": "Elaborate on your project contributions, technical challenges overcome, coursework, and tool proficiencies to reach 400-600 words.",
                "source": "Rule-Based Engine"
            })
        elif word_count > 900:
            recommendations.append({
                "category": "Resume Structure",
                "severity": "Low",
                "title": "Condense Resume to 1-2 Focused Pages",
                "evidence": f"Total length is {word_count} words. Extended resumes risk losing recruiter attention.",
                "action": "Trim non-essential details, tighten descriptions, and prioritize your most recent and relevant achievements.",
                "source": "Rule-Based Engine"
            })

        # Quantified metrics check
        if any("quantifiable" in d.lower() for d in struct_score.get("deductions", [])):
            recommendations.append({
                "category": "Impact & Metrics",
                "severity": "Medium",
                "title": "Quantify Results with Concrete Metrics",
                "evidence": "Descriptions lack quantifiable metrics (numbers, percentages, scale, speed, or volume).",
                "action": "Use the Google 'X-Y-Z' formula: 'Accomplished [X] as measured by [Y], by doing [Z]' (e.g., 'Reduced query latency by 35% through indexing optimizations').",
                "source": "Rule-Based Engine"
            })

        # Action verbs check
        if any("action verbs" in d.lower() for d in struct_score.get("deductions", [])):
            recommendations.append({
                "category": "Resume Structure",
                "severity": "Low",
                "title": "Lead Bullet Points with Dynamic Action Verbs",
                "evidence": "Limited strong action verbs were identified in bullet descriptions.",
                "action": "Begin each bullet point with high-impact verbs such as Architected, Spearheaded, Implemented, Streamlined, or Deployed.",
                "source": "Rule-Based Engine"
            })

        # Sort recommendations by severity: High first, then Medium, then Low
        severity_order = {"High": 1, "Medium": 2, "Low": 3}
        recommendations.sort(key=lambda r: severity_order.get(r.get("severity", "Low"), 4))

        return recommendations
