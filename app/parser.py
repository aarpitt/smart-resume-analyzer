"""
Resume Parser Module.
Extracts text and analyzes structural sections from PDF and DOCX files.
"""

import os
import re
from typing import Dict, List, Optional, Any
import pymupdf  # PyMuPDF
from docx import Document


class ParserError(Exception):
    """Custom exception raised when resume parsing fails or encounters invalid data."""
    pass


class ResumeParser:
    """
    Extracts text, contact details, and segmented sections from PDF and DOCX resumes.
    Handles corrupted, empty, and scanned/image-only documents gracefully.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
    MIN_TEXT_LENGTH = 60  # Minimum readable characters before flagging as empty/image-only

    # Section header detection patterns
    SECTION_PATTERNS = {
        "education": [
            r"^education\b",
            r"^academic background\b",
            r"^academic qualifications\b",
            r"^educational qualifications\b",
            r"^academic history\b",
            r"^academics\b",
            r"^qualifications\b"
        ],
        "experience": [
            r"^experience\b",
            r"^work experience\b",
            r"^professional experience\b",
            r"^employment history\b",
            r"^work history\b",
            r"^internships?\b",
            r"^relevant experience\b",
            r"^career history\b"
        ],
        "skills": [
            r"^technical skills\b",
            r"^skills & abilities\b",
            r"^skills and competencies\b",
            r"^core competencies\b",
            r"^technologies\b",
            r"^tools & technologies\b",
            r"^technical proficiencies\b",
            r"^areas of expertise\b",
            r"^key skills\b",
            r"^skills\b"
        ],
        "projects": [
            r"^projects\b",
            r"^academic projects\b",
            r"^key projects\b",
            r"^personal projects\b",
            r"^technical projects\b",
            r"^featured projects\b",
            r"^selected projects\b"
        ],
        "certifications": [
            r"^certifications?\b",
            r"^licenses & certifications?\b",
            r"^accreditations?\b",
            r"^certificates?\b",
            r"^professional certifications?\b",
            r"^courses & certifications?\b"
        ],
        "contact": [
            r"^contact information\b",
            r"^contact\b",
            r"^personal information\b",
            r"^personal details\b"
        ]
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.extension = os.path.splitext(self.filename)[1].lower()

        if self.extension not in self.ALLOWED_EXTENSIONS:
            raise ParserError(
                f"Unsupported file format '{self.extension}'. "
                "Only PDF (.pdf) and Word documents (.docx) are supported."
            )

    def extract_text(self) -> str:
        """
        Extracts raw text from the file using the appropriate engine.
        Raises ParserError for corrupt, missing, or unreadable files.
        """
        if not os.path.exists(self.file_path):
            raise ParserError("The specified file does not exist on the server.")

        if os.path.getsize(self.file_path) == 0:
            raise ParserError("The uploaded file is empty (0 bytes).")

        try:
            if self.extension == ".pdf":
                text = self._extract_from_pdf()
            elif self.extension == ".docx":
                text = self._extract_from_docx()
            else:
                raise ParserError(f"Unsupported extension: {self.extension}")
        except ParserError:
            raise
        except Exception as e:
            raise ParserError(f"Failed to process document: {str(e)}")

        cleaned_text = text.strip()
        if not cleaned_text:
            raise ParserError(
                "No readable text could be extracted from this document. "
                "It may be a scanned image or empty PDF. Please provide a text-based document."
            )

        if len(cleaned_text) < self.MIN_TEXT_LENGTH:
            raise ParserError(
                "Document contains insufficient readable text (fewer than 60 characters). "
                "The file appears to be a scanned image, photo, or placeholder."
            )

        return cleaned_text

    def _extract_from_pdf(self) -> str:
        """PyMuPDF extractor for PDF files."""
        try:
            doc = pymupdf.open(self.file_path)
        except Exception as exc:
            raise ParserError(f"Corrupted or invalid PDF file: {exc}")

        pages_text = []
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text("text")
                if text:
                    pages_text.append(text)
        finally:
            doc.close()

        full_text = "\n".join(pages_text)
        return full_text

    def _extract_from_docx(self) -> str:
        """python-docx extractor for Word files."""
        try:
            doc = Document(self.file_path)
        except Exception as exc:
            raise ParserError(f"Corrupted or invalid DOCX document: {exc}")

        paragraphs_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text:
                paragraphs_text.append(paragraph.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    paragraphs_text.append(" | ".join(row_text))

        return "\n".join(paragraphs_text)

    def parse(self) -> Dict[str, Any]:
        """
        Executes complete parsing workflow:
        1. Extract text
        2. Detect contact details
        3. Segment resume sections
        4. Calculate structural metadata
        """
        raw_text = self.extract_text()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        contact_info = self._extract_contact_info(raw_text, lines)
        sections = self._segment_sections(lines)
        word_count = len(re.findall(r"\b\w+\b", raw_text))

        return {
            "filename": self.filename,
            "raw_text": raw_text,
            "word_count": word_count,
            "line_count": len(lines),
            "contact_info": contact_info,
            "sections": sections,
            "detected_sections": [name for name, content in sections.items() if content.strip()]
        }

    def _extract_contact_info(self, text: str, lines: List[str]) -> Dict[str, Optional[str]]:
        """Extracts email, phone, LinkedIn, GitHub, portfolio link, and candidate name."""
        # Email
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        email_match = re.search(email_pattern, text)
        email = email_match.group(0) if email_match else None

        # Phone: supports (+1, +91, (123) 456-7890, 123-456-7890, etc.)
        phone_pattern = r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4})"
        phone_match = re.search(phone_pattern, text)
        phone = phone_match.group(0).strip() if phone_match else None

        # LinkedIn
        linkedin_pattern = r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|profile)\/([a-zA-Z0-9_\-]+)"
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        linkedin = linkedin_match.group(0) if linkedin_match else None

        # GitHub
        github_pattern = r"(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_\-]+)"
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        github = github_match.group(0) if github_match else None

        # Portfolio / Personal Website
        portfolio = None
        url_pattern = r"(https?:\/\/[^\s]+)"
        for url in re.findall(url_pattern, text):
            if "linkedin.com" not in url and "github.com" not in url:
                portfolio = url
                break

        # Candidate Name heuristic:
        # Check the first 4 non-empty lines for a realistic personal name (2 to 4 alphabetic words,
        # avoiding lines containing email, numbers, or section titles)
        name = None
        for line in lines[:4]:
            if any(sym in line for sym in ["@", "http", "www.", "/", "+", "(", ")", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
                continue
            cleaned_line = re.sub(r"[^a-zA-Z\s]", "", line).strip()
            words = cleaned_line.split()
            if 2 <= len(words) <= 4 and len(cleaned_line) <= 40:
                # Disallow section names like "Professional Experience"
                if not any(re.search(pat, cleaned_line.lower()) for patterns in self.SECTION_PATTERNS.values() for pat in patterns):
                    name = cleaned_line
                    break

        return {
            "name": name or "Candidate",
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "portfolio": portfolio
        }

    def _segment_sections(self, lines: List[str]) -> Dict[str, str]:
        """
        Splits text lines into recognized resume sections based on detected headers.
        """
        sections: Dict[str, List[str]] = {
            "contact": [],
            "education": [],
            "experience": [],
            "skills": [],
            "projects": [],
            "certifications": [],
            "other": []
        }

        current_section = "contact"

        for line in lines:
            line_clean = line.strip()
            line_lower = line_clean.lower()

            # Check if this line is a section header
            matched_section = None
            if len(line_clean) <= 45:  # Headers are rarely longer than 45 chars
                for section_name, patterns in self.SECTION_PATTERNS.items():
                    for pattern in patterns:
                        # Match exact header or header with trailing colon
                        if re.match(pattern, line_lower) or re.match(pattern + r"\s*:", line_lower):
                            matched_section = section_name
                            break
                    if matched_section:
                        break

            if matched_section:
                current_section = matched_section
                continue

            sections[current_section].append(line_clean)

        return {k: "\n".join(v).strip() for k, v in sections.items()}
