"""
Smart Feedback Generator Module.
Generates explainable, evidence-backed recommendations to improve resume competitiveness.
Strictly adheres to academic integrity: never fabricates experience or qualifications.
"""

from typing import Dict, List, Any


class FeedbackGenerator:
    """
    Evaluates scoring deductions and ATS role gap analysis to generate
    prioritized, actionable improvement recommendations with transparent evidence.
    """

    def generate_recommendations(
        self,
        parsed_data: Dict[str, Any],
        scoring_result: Dict[str, Any],
        ats_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Produces a prioritized list of actionable recommendations with evidence and impact rating.
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
                "action": "Include an active email using a professional name format (e.g., firstname.lastname@example.com) at the top of the resume."
            })

        if not contact.get("phone"):
            recommendations.append({
                "category": "Contact Details",
                "severity": "High",
                "title": "Include a Direct Phone Number",
                "evidence": "No standard telephone contact number was identified.",
                "action": "Provide a phone number with country code so recruiters can easily schedule phone screens."
            })

        if not contact.get("linkedin") and not contact.get("github"):
            recommendations.append({
                "category": "Contact Details",
                "severity": "Medium",
                "title": "Add Professional Profile Links (LinkedIn / GitHub)",
                "evidence": "Neither a LinkedIn profile URL nor a GitHub repository was detected.",
                "action": "Link to your public LinkedIn profile and GitHub account to provide verification of your background and code samples."
            })
        elif not contact.get("github") and ats_result.get("target_role") in ["Web Developer", "AI Engineer", "Cloud Engineer"]:
            recommendations.append({
                "category": "Contact Details",
                "severity": "Medium",
                "title": "Add GitHub / Code Repository Link",
                "evidence": f"A GitHub link was not detected, which is standard for {ats_result.get('target_role')} applicants.",
                "action": "Add a link to your GitHub account showcasing clean repositories, README documentation, and open-source contributions."
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
                "action": f"If you have experience or academic coursework with any of these ({', '.join(top_missing)}), explicitly mention them in your Skills and Projects sections."
            })

        missing_rec = ats_result.get("missing_recommended_skills", [])
        if len(missing_rec) >= 4 and not missing_req:
            top_rec = missing_rec[:3]
            recommendations.append({
                "category": "Role Alignment",
                "severity": "Low",
                "title": "Add Secondary Industry Tools to Stand Out",
                "evidence": f"While core skills are present, incorporating complementary tools like {', '.join(top_rec)} will elevate your profile above average applicants.",
                "action": "Highlight familiarity with complementary frameworks, tools, or libraries used in modern team environments."
            })

        # 3. Education Recommendations
        edu_score = scoring_result.get("breakdown", {}).get("education", {})
        if "education" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Education",
                "severity": "High",
                "title": "Add a Dedicated Education Section",
                "evidence": "No distinct 'Education' section heading was identified.",
                "action": "Create an 'Education' section listing your degree, major, university/college name, and graduation year."
            })
        elif edu_score.get("deductions"):
            recommendations.append({
                "category": "Education",
                "severity": "Medium",
                "title": "Clarify Academic Credentials",
                "evidence": "; ".join(edu_score.get("deductions", [])),
                "action": "Clearly state your degree type (e.g., B.S., B.Tech, Master's) alongside the full institution name and graduation timeline."
            })

        # 4. Projects Recommendations
        proj_score = scoring_result.get("breakdown", {}).get("projects", {})
        if "projects" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Projects",
                "severity": "High",
                "title": "Add a Dedicated Projects Section",
                "evidence": "Technical recruiters prioritize practical implementations, but no 'Projects' section was detected.",
                "action": "Add 2-3 substantial projects detailing what you built, the tech stack utilized, your role, and the outcome."
            })
        elif proj_score.get("score", 0) < 14:
            recommendations.append({
                "category": "Projects",
                "severity": "Medium",
                "title": "Deepen Project Descriptions with Tech Stack and Impact",
                "evidence": "Existing project entries are brief or lack technical implementation details and results.",
                "action": "Structure each project entry with: Problem statement, Technologies utilized, and Quantifiable results or user impact."
            })

        # 5. Experience Recommendations
        exp_score = scoring_result.get("breakdown", {}).get("experience", {})
        if "experience" not in parsed_data.get("detected_sections", []):
            recommendations.append({
                "category": "Work Experience",
                "severity": "Medium",
                "title": "Add Practical Experience or Relevant Internships",
                "evidence": "No 'Experience' or 'Work History' section was recognized.",
                "action": "If you have prior internships, freelance contracts, research assistantships, or student leadership roles, document them chronologically with responsibilities."
            })
        elif exp_score.get("score", 0) < 10:
            recommendations.append({
                "category": "Work Experience",
                "severity": "Medium",
                "title": "Standardize Job Titles and Timeline Dates",
                "evidence": "Job titles or employment date ranges are ambiguous or missing.",
                "action": "Explicitly format each position with: Role Title, Company/Organization Name, Location, and Date Range (e.g., 'May 2023 - Aug 2023')."
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
                "action": "Elaborate on your project contributions, technical challenges overcome, coursework, and tool proficiencies to reach 400-600 words."
            })
        elif word_count > 900:
            recommendations.append({
                "category": "Resume Structure",
                "severity": "Low",
                "title": "Condense Resume to 1-2 Focused Pages",
                "evidence": f"Total length is {word_count} words. Extended resumes risk losing recruiter attention.",
                "action": "Trim non-essential details, tighten descriptions, and prioritize your most recent and relevant achievements."
            })

        # Quantified metrics check
        if any("quantifiable" in d.lower() for d in struct_score.get("deductions", [])):
            recommendations.append({
                "category": "Impact & Metrics",
                "severity": "Medium",
                "title": "Quantify Results with Concrete Metrics",
                "evidence": "Descriptions lack quantifiable metrics (numbers, percentages, scale, speed, or volume).",
                "action": "Use the Google 'X-Y-Z' formula: 'Accomplished [X] as measured by [Y], by doing [Z]' (e.g., 'Reduced query latency by 35% through indexing optimizations')."
            })

        # Action verbs check
        if any("action verbs" in d.lower() for d in struct_score.get("deductions", [])):
            recommendations.append({
                "category": "Resume Structure",
                "severity": "Low",
                "title": "Lead Bullet Points with Dynamic Action Verbs",
                "evidence": "Limited strong action verbs were identified in bullet descriptions.",
                "action": "Begin each bullet point with high-impact verbs such as Architected, Spearheaded, Implemented, Streamlined, or Deployed."
            })

        # Sort recommendations by severity: High first, then Medium, then Low
        severity_order = {"High": 1, "Medium": 2, "Low": 3}
        recommendations.sort(key=lambda r: severity_order.get(r.get("severity", "Low"), 4))

        return recommendations
