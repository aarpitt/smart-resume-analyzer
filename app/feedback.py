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

    @staticmethod
    def sanitize_invented_metrics(text: str) -> str:
        """
        Sanitizes recommendations to ensure illustrative examples never contain
        invented numerical values (such as '$1.2M' or '15%').
        Replaces fabricated illustrative metrics with guidance advising users to supply
        their actual, verifiable metrics.
        """
        if not text:
            return text

        # 1. Parenthetical examples containing dollar amounts or percentages
        text = re.sub(
            r'\([^)]*?(?:\$|\b\d+(?:\.\d+)?\s*%(?!\s*(?:credit|weight)))[^)]*?\)',
            '(incorporating your actual, verifiable metrics where available)',
            text,
            flags=re.IGNORECASE
        )

        # 2. Illustrative clauses starting with such as / for example / e.g. with dollar amounts or percentages
        text = re.sub(
            r'\b(?:such as|for example|for instance|e\.g\.)\s+[^,;\n]+?(?:\$|\b\d+(?:\.\d+)?\s*%(?!\s*(?:credit|weight)))[^,;\n]*(?:(?=\.)|$|,|;)',
            'incorporating your actual, verifiable metrics where available',
            text,
            flags=re.IGNORECASE
        )

        # Clean up double punctuation or awkward spacing
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        return text.strip()

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

        is_custom = ats_result.get("is_custom_job", False)

        if is_custom:
            system_prompt = (
                f"You are an Executive Career Advisor and Expert Resume Strategist evaluating a candidate for the role of '{target_role}'.\n"
                f"Analyze the candidate's resume diagnostics against the target job requirements and generate 3 to 5 "
                f"high-impact, actionable, and explainable recommendations tailored strictly to this profession.\n\n"
                f"STRICT PROFESSION-NEUTRAL RULES:\n"
                f"1. ADAPT TO THE TARGET ROLE: You are evaluating a candidate for '{target_role}'.\n"
                f"   - DO NOT recommend programming languages, software repositories (GitHub), Docker, Kubernetes, SQL, or DevOps tools unless they explicitly appear in the job requirements.\n"
                f"   - For managerial, operational, or business roles (e.g. Project Manager, Product Manager, Operations, Financial Analyst), focus on leadership evidence, budget oversight, risk management, methodology application (e.g. Agile/Scrum/PMP), stakeholder alignment, and delivered outcomes.\n"
                f"2. Output MUST be a valid JSON object with root key 'recommendations' containing a list of objects.\n"
                f"3. Each object must have these exact keys:\n"
                f"   - 'category': One of ['Role Alignment', 'Professional Competencies', 'Technical Skills', 'Projects', 'Work Experience', 'Education', 'Contact Details', 'Resume Structure', 'Impact & Metrics']\n"
                f"   - 'severity': Exactly one of ['High', 'Medium', 'Low']\n"
                f"   - 'title': Concise actionable title (under 10 words)\n"
                f"   - 'evidence': Clear factual summary of what was found or missing in the resume\n"
                f"   - 'action': Concrete instruction on how to address this gap.\n"
                f"4. ZERO FABRICATION & STRICT ACADEMIC INTEGRITY:\n"
                f"   - NEVER fabricate fictional past jobs, companies, dates, degrees, or numerical statistics.\n"
                f"   - ABSOLUTELY FORBIDDEN TO INVENT SPECIFIC NUMERICAL VALUES: Never suggest specific invented achievements or numerical results (such as '$1.2M project budget', '15% improvement', or '$500K savings') as facts about the candidate or even as illustrative parenthetical examples.\n"
                f"   - Do NOT provide illustrative examples containing invented numbers (e.g., do NOT write '(e.g., forecasted $1.2M budget and achieved 5% cost savings)').\n"
                f"   - INSTEAD: Explicitly recommend that candidates quantify their achievements by including their OWN ACTUAL, VERIFIABLE METRICS and figures where available from their real work history."
            )
            user_content = (
                f"Candidate Diagnostics (CUSTOM JOB DESCRIPTION ANALYSIS MODE):\n"
                f"- Target Job Title: {target_role}\n"
                f"- Overall Resume Quality Score: {overall_score}/100 (Grade {grade}, {tier})\n"
                f"- Word Count: {word_count}\n"
                f"- Contact Detected: Email={'Yes' if contact.get('email') else 'No'}, "
                f"Phone={'Yes' if contact.get('phone') else 'No'}, "
                f"LinkedIn={'Yes' if contact.get('linkedin') else 'No'}\n"
                f"- Missing Required Job Competencies: {', '.join(missing_required) if missing_required else 'None'}\n"
                f"- Matched Job Competencies: {', '.join(matched_required) if matched_required else 'None'}\n"
                f"- Missing Preferred Competencies: {', '.join(missing_recommended[:5]) if missing_recommended else 'None'}\n"
                f"- Key Job Responsibilities: {', '.join(ats_result.get('key_responsibilities', [])[:4])}\n"
                f"- Detected Weaknesses & Deductions:\n" +
                "\n".join(f"  * {d}" for d in deductions_summary[:5]) +
                f"\n\nCRITICAL CONSTRAINTS:\n"
                f"1. All recommendations must directly pertain to {target_role}. Prioritize missing or unevidenced competencies from the job description.\n"
                f"2. Do NOT suggest software development tools (GitHub, Docker, Kubernetes, SQL, Python) unless present in the job requirements above.\n"
                f"3. NEVER fabricate or invent specific numbers, dollar amounts, or percentages (e.g. '$1.2M', '15%'). Always instruct the candidate to include their actual, verifiable metrics where available."
            )
        else:
            system_prompt = (
                "You are a Senior Technical Recruiter and AI Resume Advisor.\n"
                "Analyze the candidate's automated resume evaluation diagnostics and generate 3 to 5 "
                "high-impact, actionable, and explainable recommendations.\n\n"
                "STRICT RULES & CONSTRAINTS:\n"
                "1. Output MUST be a valid JSON object with root key 'recommendations' containing a list of objects.\n"
                "2. Each object must have these exact keys:\n"
                "   - 'category': One of ['Role Alignment', 'Technical Skills', 'Projects', 'Work Experience', 'Education', 'Contact Details', 'Resume Structure', 'Impact & Metrics']\n"
                "   - 'severity': Exactly one of ['High', 'Medium', 'Low']\n"
                "   - 'title': Concise actionable title (under 10 words)\n"
                "   - 'evidence': Clear factual summary of what was found or missing in the resume\n"
                "   - 'action': Concrete instruction on how to address this gap.\n"
                "3. ZERO FABRICATION & STRICT ACADEMIC INTEGRITY:\n"
                "   - NEVER fabricate or invent fictional past job titles, employers, companies, dates, or degrees.\n"
                "   - ABSOLUTELY FORBIDDEN TO INVENT SPECIFIC NUMERICAL VALUES: Never invent dollar amounts, percentages (such as '15% improvement'), or performance metrics as facts about the candidate or even as illustrative examples.\n"
                "   - Do NOT provide illustrative examples with invented numbers (e.g., do NOT write 'reduced latency by 35%' or 'saved $1M').\n"
                "   - INSTEAD: Recommend that candidates incorporate their OWN ACTUAL, VERIFIABLE METRICS from their authentic experience where available using frameworks like Google X-Y-Z: 'Accomplished [X] as measured by [Y], by doing [Z]'.\n"
                "   - If suggesting missing tools, always frame as conditional: 'If you have coursework, personal projects, or lab experience with [Skill], explicitly document it...'.\n"
                "   - Emphasize authentic, truthful presentation of the candidate's real capabilities."
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
                "\n".join(f"  * {d}" for d in deductions_summary[:6]) +
                f"\n\nCRITICAL: Never invent specific numerical metrics (e.g. '$1.2M' or '15%'). Direct the candidate to include their actual, verifiable metrics where available."
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
                            raw_title = item.get("title", "Resume Improvement")
                            raw_evidence = item.get("evidence", "Identified through ATS structural analysis.")
                            raw_action = item.get("action", "")
                            cleaned_recs.append({
                                "category": category,
                                "severity": severity,
                                "title": self.sanitize_invented_metrics(raw_title),
                                "evidence": self.sanitize_invented_metrics(raw_evidence),
                                "action": self.sanitize_invented_metrics(raw_action),
                                "source": f"AI (Groq: {model_id.split('/')[-1]})"
                            })

                    if cleaned_recs:
                        if is_custom:
                            # Defensive sanitizer: purge irrelevant technical tools if absent from custom JD
                            jd_context = (
                                target_role + " " +
                                " ".join(ats_result.get("matched_required_skills", [])) + " " +
                                " ".join(ats_result.get("missing_required_skills", [])) + " " +
                                " ".join(ats_result.get("missing_recommended_skills", [])) + " " +
                                " ".join(ats_result.get("key_responsibilities", []))
                            ).lower()
                            technical_blacklist = ["github", "docker", "kubernetes", "k8s", "sql", "devops", "ci/cd", "react", "python", "javascript", "code repository", "code repo"]
                            sanitized = []
                            for rec in cleaned_recs:
                                rec_text = (rec.get("title", "") + " " + rec.get("action", "") + " " + rec.get("evidence", "")).lower()
                                is_inappropriate = False
                                for term in technical_blacklist:
                                    if re.search(r"\b" + re.escape(term) + r"\b", rec_text) and not re.search(r"\b" + re.escape(term) + r"\b", jd_context):
                                        is_inappropriate = True
                                        break
                                if not is_inappropriate:
                                    sanitized.append(rec)
                            if len(sanitized) >= 2:
                                cleaned_recs = sanitized

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

        is_custom = ats_result.get("is_custom_job", False)

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

        if is_custom:
            # Profession-neutral contact recommendations: LinkedIn is primary; GitHub is not required
            if not contact.get("linkedin"):
                recommendations.append({
                    "category": "Contact Details",
                    "severity": "Medium",
                    "title": "Add Professional Profile Link (LinkedIn)",
                    "evidence": "No professional LinkedIn profile URL was detected in the document header.",
                    "action": "Include a link to your public LinkedIn profile to allow hiring managers to review your professional background and endorsements.",
                    "source": "Rule-Based Engine"
                })
        else:
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
            title = f"Address Missing Core Competencies for {ats_result.get('target_role')}" if is_custom else f"Address Core Skill Gaps for {ats_result.get('target_role')}"
            action_text = (
                f"If you have practical experience or training with any of these ({', '.join(top_missing)}), explicitly document them with concrete examples in your experience and competencies sections."
                if is_custom else
                f"If you have experience or academic coursework with any of these ({', '.join(top_missing)}), explicitly mention them in your Skills and Projects sections."
            )
            recommendations.append({
                "category": "Role Alignment",
                "severity": "High",
                "title": title,
                "evidence": f"Essential required competencies for this role are missing from your resume: {', '.join(top_missing)}.",
                "action": action_text,
                "source": "Rule-Based Engine"
            })

        # Check for competencies that were merely mentioned rather than verified in work history
        matched_details = ats_result.get("matched_required_details", [])
        mentioned_only = [item["competency"] for item in matched_details if "Mentioned" in item.get("evidence", "")]
        if mentioned_only:
            top_mentioned = mentioned_only[:3]
            recommendations.append({
                "category": "Work Experience",
                "severity": "Medium",
                "title": "Demonstrate Practical Evidence for Key Competencies",
                "evidence": f"Competencies like {', '.join(top_mentioned)} were found in your skills inventory or summary but lack demonstrated accomplishment statements in your work experience or projects.",
                "action": f"Add specific bullet points to your experience describing how you practically utilized ({', '.join(top_mentioned)}) in previous roles.",
                "source": "Rule-Based Engine"
            })

        missing_rec = ats_result.get("missing_recommended_skills", [])
        if len(missing_rec) >= 4 and not missing_req:
            top_rec = missing_rec[:3]
            title = "Incorporate Preferred Industry Qualifications" if is_custom else "Add Secondary Industry Tools to Stand Out"
            evidence_text = f"While core requirements are met, incorporating preferred competencies like {', '.join(top_rec)} will elevate your profile for {ats_result.get('target_role')}."
            action_text = (
                f"Highlight familiarity with ({', '.join(top_rec)}) to strengthen your competitive positioning."
                if is_custom else
                "Highlight familiarity with complementary frameworks, tools, or libraries used in modern team environments."
            )
            recommendations.append({
                "category": "Role Alignment",
                "severity": "Low",
                "title": title,
                "evidence": evidence_text,
                "action": action_text,
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
                "severity": "Medium" if is_custom else "High",
                "title": "Document Key Projects or Major Initiatives" if is_custom else "Add a Dedicated Projects Section",
                "evidence": "No dedicated 'Projects' or 'Key Initiatives' section was detected in your resume." if is_custom else "Technical recruiters prioritize practical implementations, but no 'Projects' section was detected.",
                "action": "Add 2-3 substantial projects or organizational initiatives detailing the challenge, your leadership role, methods utilized, and outcomes." if is_custom else "Add 2-3 substantial projects detailing what you built, the tech stack utilized, your role, and the outcome.",
                "source": "Rule-Based Engine"
            })
        elif proj_score.get("score", 0) < 14:
            recommendations.append({
                "category": "Projects",
                "severity": "Medium",
                "title": "Deepen Project Descriptions with Scope and Deliverables" if is_custom else "Deepen Project Descriptions with Tech Stack and Impact",
                "evidence": "Existing project entries are brief or lack context on project scale, deliverables, and demonstrated results." if is_custom else "Existing project entries are brief or lack technical implementation details and results.",
                "action": "Structure each project entry with: Problem/Goal, Strategy and Tools utilized, and Measurable business results." if is_custom else "Structure each project entry with: Problem statement, Technologies utilized, and Quantifiable results or user impact.",
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
                "action": (
                    "Incorporate your actual, verifiable metrics where available using the Google 'X-Y-Z' formula: "
                    "'Accomplished [X] as measured by [Y], by doing [Z]' (substituting your verified project figures, efficiency improvements, or team scale)."
                ),
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

        # If profile has zero detected deficiencies (exceptional resume), provide advanced career enhancement advice
        if not recommendations:
            if is_custom:
                recommendations.append({
                    "category": "Role Alignment",
                    "severity": "Low",
                    "title": f"Pursue Advanced Leadership & Credentials for {ats_result.get('target_role')}",
                    "evidence": f"Your resume demonstrates comprehensive alignment ({scoring_result.get('overall_score')}/100) with all core requirements for {ats_result.get('target_role')}.",
                    "action": "Consider highlighting specialized professional certifications, executive leadership achievements, or case studies to further differentiate your profile.",
                    "source": "Rule-Based Engine"
                })
                recommendations.append({
                    "category": "Impact & Metrics",
                    "severity": "Low",
                    "title": "Emphasize Strategic and Organizational ROI",
                    "evidence": "All baseline structural sections, competency depth, and contact standards are fully satisfied.",
                    "action": "Ensure project and experience descriptions emphasize long-term strategic value, cross-functional leadership, and measurable operational results.",
                    "source": "Rule-Based Engine"
                })
            else:
                recommendations.append({
                    "category": "Role Alignment",
                    "severity": "Low",
                    "title": f"Pursue Advanced Specializations for {ats_result.get('target_role')}",
                    "evidence": f"Your resume demonstrates comprehensive alignment ({scoring_result.get('overall_score')}/100) with all core requirements for {ats_result.get('target_role')}.",
                    "action": "Consider highlighting technical articles, open-source library contributions, or system architecture case studies to further elevate your profile.",
                    "source": "Rule-Based Engine"
                })
                recommendations.append({
                    "category": "Impact & Metrics",
                    "severity": "Low",
                    "title": "Highlight Long-Term System & Business ROI",
                    "evidence": "All baseline structural sections, technical depth, and contact standards are fully satisfied.",
                    "action": "For senior technical evaluations, ensure project descriptions emphasize operational reliability, team leadership, and measurable business impact.",
                    "source": "Rule-Based Engine"
                })

        return recommendations
