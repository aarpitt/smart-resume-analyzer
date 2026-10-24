"""
ATS (Applicant Tracking System) Analyzer Module.
Performs normalized skill extraction, alias resolution, role matching,
and scikit-learn TF-IDF semantic profile similarity analysis.
"""

import json
import os
import re
from typing import Dict, List, Set, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ATSAnalyzer:
    """
    Evaluates resume compatibility against target job profiles:
    - Data Analyst
    - Web Developer
    - AI Engineer
    - Cloud Engineer
    """

    SUPPORTED_ROLES = [
        "Data Analyst",
        "Web Developer",
        "AI Engineer",
        "Cloud Engineer"
    ]

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "data", "role_skills.json"
            )
        self.config_path = config_path
        self.roles_data, self.aliases, self.categories = self._load_config(config_path)
        self.compiled_patterns = self._precompile_patterns()

    def _load_config(self, path: str) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str]]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Role skills configuration not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return (
            data.get("roles", {}),
            data.get("aliases", {}),
            data.get("skill_categories", {})
        )

    def _build_regex(self, term: str) -> re.Pattern:
        """Constructs a safe regex pattern respecting boundary characters and symbols."""
        escaped = re.escape(term)
        prefix = r"\b" if re.match(r"^\w", term) else r"(?:^|[\s(\[{<\"'])"
        suffix = r"\b" if re.search(r"\w$", term) else r"(?:$|[\s)\]}>\"',.!?:;])"
        return re.compile(prefix + escaped + suffix, re.IGNORECASE)

    def _precompile_patterns(self) -> Dict[str, Tuple[re.Pattern, str]]:
        """
        Precompiles patterns for all canonical skills and aliases.
        Returns mapping: search_term -> (compiled_regex, canonical_skill_name)
        """
        patterns = {}

        # 1. All canonical skills defined across roles and categories
        all_canonical = set(self.categories.keys())
        for role_info in self.roles_data.values():
            all_canonical.update(role_info.get("required_skills", []))
            all_canonical.update(role_info.get("recommended_skills", []))

        for skill in all_canonical:
            patterns[skill] = (self._build_regex(skill), skill)

        # 2. Aliases mapped to canonical names
        for alias, canonical in self.aliases.items():
            patterns[alias] = (self._build_regex(alias), canonical.lower())

        return patterns

    def extract_all_skills(self, text: str) -> List[str]:
        """
        Extracts all recognized technical skills present in the text,
        normalizing aliases to canonical skill names.
        """
        matched_canonical: Set[str] = set()

        for term, (pattern, canonical) in self.compiled_patterns.items():
            if pattern.search(text):
                matched_canonical.add(canonical)

        return sorted(list(matched_canonical))

    def calculate_tfidf_similarity(self, resume_text: str, target_role: str) -> float:
        """
        Uses scikit-learn TfidfVectorizer and Cosine Similarity to compare the
        resume's semantic content with the role's benchmark profile.
        Returns a score between 0.0 and 1.0.
        """
        role_info = self.roles_data.get(target_role)
        if not role_info:
            return 0.0

        benchmark = role_info.get("benchmark_profile", "")
        # Add required skills to benchmark to reinforce role vocabulary
        role_vocabulary = " ".join(role_info.get("required_skills", []) + role_info.get("recommended_skills", []))
        augmented_benchmark = f"{benchmark} {role_vocabulary}"

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=500
            )
            tfidf_matrix = vectorizer.fit_transform([resume_text, augmented_benchmark])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(max(0.0, min(1.0, similarity)))
        except Exception:
            return 0.0

    def analyze_role_compatibility(self, resume_text: str, target_role: str) -> Dict[str, Any]:
        """
        Conducts full ATS role compatibility analysis:
        - Extracts normalized skills
        - Evaluates required vs missing skills for target role
        - Evaluates recommended skills
        - Calculates semantic similarity via TF-IDF
        - Computes composite ATS Match %
        """
        if target_role not in self.roles_data:
            target_role = "Data Analyst"  # Default fallback

        role_info = self.roles_data[target_role]
        required_skills = [s.lower() for s in role_info.get("required_skills", [])]
        recommended_skills = [s.lower() for s in role_info.get("recommended_skills", [])]

        extracted_skills = self.extract_all_skills(resume_text)
        extracted_set = set(extracted_skills)

        # Match calculation
        matched_required = [s for s in required_skills if s in extracted_set]
        missing_required = [s for s in required_skills if s not in extracted_set]

        matched_recommended = [s for s in recommended_skills if s in extracted_set]
        missing_recommended = [s for s in recommended_skills if s not in extracted_set]

        # Other detected skills not directly in role requirements
        role_skills_all = set(required_skills).union(set(recommended_skills))
        other_skills = [s for s in extracted_skills if s not in role_skills_all]

        # Percentages
        req_total = len(required_skills)
        req_matched_count = len(matched_required)
        req_pct = (req_matched_count / req_total * 100) if req_total > 0 else 0

        rec_total = len(recommended_skills)
        rec_matched_count = len(matched_recommended)
        rec_pct = (rec_matched_count / rec_total * 100) if rec_total > 0 else 0

        # Scikit-learn TF-IDF semantic similarity
        tfidf_similarity = self.calculate_tfidf_similarity(resume_text, target_role)
        tfidf_pct = round(tfidf_similarity * 100, 1)

        # Composite ATS Score:
        # 60% Required Skills Match + 20% Recommended Skills Match + 20% TF-IDF Cosine Similarity
        composite_score = (0.60 * req_pct) + (0.20 * rec_pct) + (0.20 * tfidf_pct)
        composite_score = round(max(0, min(100, composite_score)))

        # Categorize matched skills for dashboard display
        categorized_matched = {}
        for skill in matched_required + matched_recommended:
            category = self.categories.get(skill, "Technical")
            categorized_matched.setdefault(category, []).append(skill.title())

        return {
            "target_role": target_role,
            "role_title": role_info.get("title", target_role),
            "role_description": role_info.get("description", ""),
            "ats_score": composite_score,
            "tfidf_similarity_score": tfidf_pct,
            "required_skills_count": req_total,
            "required_matched_count": req_matched_count,
            "required_match_percentage": round(req_pct, 1),
            "recommended_skills_count": rec_total,
            "recommended_matched_count": rec_matched_count,
            "recommended_match_percentage": round(rec_pct, 1),
            "matched_required_skills": [s.title() for s in matched_required],
            "missing_required_skills": [s.title() for s in missing_required],
            "matched_recommended_skills": [s.title() for s in matched_recommended],
            "missing_recommended_skills": [s.title() for s in missing_recommended],
            "all_extracted_skills": [s.title() for s in extracted_skills],
            "other_detected_skills": [s.title() for s in other_skills],
            "categorized_matched_skills": categorized_matched
        }
