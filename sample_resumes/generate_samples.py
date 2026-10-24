"""
Generates realistic sample resumes in both PDF and DOCX formats for testing and academic demonstrations.
"""

import os
import pymupdf
from docx import Document


def create_docx_resume(filepath: str, title_name: str, email: str, phone: str, linkedin: str, github: str,
                       summary: str, skills: list, experience: list, projects: list, education: list):
    doc = Document()

    # Header
    doc.add_heading(title_name, level=0)
    contact_p = doc.add_paragraph()
    contact_parts = []
    if email: contact_parts.append(email)
    if phone: contact_parts.append(phone)
    if linkedin: contact_parts.append(linkedin)
    if github: contact_parts.append(github)
    contact_p.text = " | ".join(contact_parts)

    # Summary
    if summary:
        doc.add_heading("Professional Summary", level=1)
        doc.add_paragraph(summary)

    # Technical Skills
    if skills:
        doc.add_heading("Technical Skills", level=1)
        doc.add_paragraph(", ".join(skills))

    # Experience
    if experience:
        doc.add_heading("Work Experience", level=1)
        for job in experience:
            p = doc.add_paragraph()
            p.add_run(f"{job['role']} - {job['company']} ({job['dates']})\n").bold = True
            for point in job['bullets']:
                doc.add_paragraph(point, style="List Bullet")

    # Projects
    if projects:
        doc.add_heading("Projects", level=1)
        for proj in projects:
            p = doc.add_paragraph()
            p.add_run(f"{proj['name']} | {proj['tech']}\n").bold = True
            for pt in proj['bullets']:
                doc.add_paragraph(pt, style="List Bullet")

    # Education
    if education:
        doc.add_heading("Education", level=1)
        for edu in education:
            p = doc.add_paragraph()
            p.add_run(f"{edu['degree']} - {edu['school']} ({edu['dates']})")

    doc.save(filepath)
    print(f"Generated DOCX: {filepath}")


def create_pdf_resume(filepath: str, text_content: str):
    doc = pymupdf.open()
    page = doc.new_page()
    # PyMuPDF insert_text
    rect = pymupdf.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, text_content, fontsize=10, fontname="helv")
    doc.save(filepath)
    doc.close()
    print(f"Generated PDF: {filepath}")


def main():
    samples_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. AI Engineer Sample (DOCX)
    create_docx_resume(
        os.path.join(samples_dir, "sample_ai_engineer.docx"),
        title_name="Alex Chen",
        email="alex.chen.ai@example.com",
        phone="+1 (555) 234-5678",
        linkedin="https://linkedin.com/in/alexchen-ai",
        github="https://github.com/alexchen-ml",
        summary="AI and Machine Learning Engineer with 3+ years experience building predictive systems and deep learning models.",
        skills=["Python", "PyTorch", "TensorFlow", "scikit-learn", "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Docker", "Pandas", "NumPy", "Hugging Face"],
        experience=[
            {
                "role": "Machine Learning Engineer",
                "company": "Cognitive Solutions Inc.",
                "dates": "2022 - Present",
                "bullets": [
                    "Engineered deep learning architectures using PyTorch and Transformers, improving inference throughput by 35%.",
                    "Automated data preprocessing pipelines for 10TB of NLP text data, reducing feature engineering turnaround by 40%."
                ]
            },
            {
                "role": "AI Research Intern",
                "company": "DeepTech Labs",
                "dates": "2021 - 2022",
                "bullets": [
                    "Developed computer vision models with OpenCV and TensorFlow, achieving 94% classification accuracy.",
                    "Collaborated on model deployment using Docker containers and REST API endpoints."
                ]
            }
        ],
        projects=[
            {
                "name": "Neural Semantic Search Engine",
                "tech": "PyTorch, Transformers, Hugging Face, Docker",
                "bullets": [
                    "Architected semantic search retrieval serving 50,000 queries daily with sub-80ms latency.",
                    "Fine-tuned transformer models yielding a 22% improvement in Mean Reciprocal Rank (MRR)."
                ]
            },
            {
                "name": "Automated Medical Image Classifier",
                "tech": "TensorFlow, scikit-learn, OpenCV, Python",
                "bullets": [
                    "Trained convolutional neural network (CNN) on 25,000 images, reducing diagnostic false positives by 18%."
                ]
            }
        ],
        education=[
            {"degree": "Master of Science in Computer Science (AI Track)", "school": "State University Institute", "dates": "2020 - 2022"},
            {"degree": "Bachelor of Technology in Computer Engineering", "school": "National Institute of Technology", "dates": "2016 - 2020"}
        ]
    )

    # 2. Web Developer Sample (DOCX)
    create_docx_resume(
        os.path.join(samples_dir, "sample_web_developer.docx"),
        title_name="Sarah Miller",
        email="sarah.miller.dev@example.com",
        phone="+1 415-555-0199",
        linkedin="https://linkedin.com/in/sarahmiller-dev",
        github="https://github.com/sarahmiller-web",
        summary="Full Stack Web Developer specialized in modern JavaScript, React, Node.js, and scalable cloud architectures.",
        skills=["JavaScript", "TypeScript", "React", "Node.js", "Express", "HTML5", "CSS3", "Git", "REST API", "MongoDB", "PostgreSQL", "Responsive Design", "Bootstrap"],
        experience=[
            {
                "role": "Full Stack Web Developer",
                "company": "PixelCraft Studios",
                "dates": "2021 - Present",
                "bullets": [
                    "Architected high-volume web applications using React, TypeScript, and Node.js serving over 200,000 active users.",
                    "Engineered RESTful APIs with Express and PostgreSQL, reducing endpoint response latency by 28%."
                ]
            },
            {
                "role": "Frontend Developer Intern",
                "company": "Nexus Web Solutions",
                "dates": "2020 - 2021",
                "bullets": [
                    "Designed accessible, mobile-responsive user interfaces adhering to WCAG 2.1 accessibility standards.",
                    "Streamlined Git version control branching workflows across a cross-functional team of 8 engineers."
                ]
            }
        ],
        projects=[
            {
                "name": "E-Commerce SaaS Platform",
                "tech": "React, Node.js, Express, MongoDB, REST API",
                "bullets": [
                    "Constructed secure checkout microservice handling $1.2M in annual recurring transactions.",
                    "Optimized bundle size and component caching to improve Lighthouse page performance score to 96."
                ]
            },
            {
                "name": "Collaborative Task Workspace",
                "tech": "TypeScript, React, PostgreSQL, HTML5, CSS3",
                "bullets": [
                    "Built real-time task manager supporting team workspaces with instant websocket synchronization."
                ]
            }
        ],
        education=[
            {"degree": "Bachelor of Science in Information Technology", "school": "Metropolitan College University", "dates": "2017 - 2021"}
        ]
    )

    # 3. Data Analyst Sample (PDF)
    data_analyst_text = """Maya Patel
maya.patel.analytics@example.com | +1 (650) 555-0143
https://linkedin.com/in/mayapatel-data | https://github.com/mayapatel-analytics

Professional Summary
Detail-oriented Data Analyst with 3 years of experience transforming complex commercial data into actionable strategic insights. Expertise in SQL database querying, predictive modeling in Python, and executive dashboard development in Tableau and Power BI.

Technical Skills
SQL, Python, Excel, Pandas, NumPy, Power BI, Tableau, Data Visualization, Statistics, ETL, Data Cleaning, Data Modeling, A/B Testing, Business Intelligence

Work Experience
Data Analyst - Retail Insights Corp (2022 - Present)
- Formulated SQL queries across multi-million row relational databases to quantify customer retention rates, increasing LTV by 14%.
- Designed automated Power BI and Tableau KPI dashboards utilized daily by C-suite executives for operational decisions.
- Conducted hypothesis testing and A/B testing on pricing models, resulting in an annualized $340,000 revenue lift.

Junior Data Analyst - FinMetrics (2021 - 2022)
- Built automated ETL data cleaning pipelines using Python and Pandas, saving 15 hours of manual data preparation weekly.
- Produced statistical reports analyzing churn correlation using regression and hypothesis testing.

Key Projects
Customer Lifetime Value Predictive Engine
Technologies: Python, SQL, Pandas, NumPy, Statistics, Scikit-learn
- Analyzed 500,000 transactional records to segment customer churn cohorts.
- Delivered interactive visualization dashboards communicating risk factors to commercial managers.

E-Commerce Conversion Analysis Dashboard
Technologies: Power BI, SQL, Excel, Data Modeling
- Centralized fragmented marketing analytics from Google Analytics and internal databases into a single BI model.

Education
Bachelor of Science in Statistics and Data Science
University of Washington, Seattle (2017 - 2021)
"""
    create_pdf_resume(os.path.join(samples_dir, "sample_data_analyst.pdf"), data_analyst_text)

    # 4. Cloud Engineer Sample (PDF)
    cloud_engineer_text = """Marcus Vance
marcus.vance.cloud@example.com | +1 (206) 555-8831
https://linkedin.com/in/marcusvance-cloud | https://github.com/marcusvance-ops

Professional Summary
Senior Cloud & DevOps Engineer specializing in scalable AWS cloud infrastructure, Kubernetes orchestration, Infrastructure as Code with Terraform, and zero-downtime CI/CD deployment pipelines.

Technical Skills
AWS, Docker, Kubernetes, Linux, Terraform, CI/CD, Bash, Infrastructure as Code, Azure, Microservices, Prometheus, Grafana, Git, Networking, IAM

Work Experience
Cloud Infrastructure Engineer - CloudScale Systems (2022 - Present)
- Architected multi-region AWS cloud environments using Terraform Infrastructure as Code (IaC), decreasing provisioning times by 65%.
- Administered Kubernetes clusters hosting 40+ microservices with 99.99% uptime availability.
- Automated CI/CD deployment pipelines utilizing Git and Bash scripting, shortening release cycles from bi-weekly to daily.

Linux Systems Administrator - Enterprise Cloud Net (2020 - 2022)
- Managed 120+ Red Hat Linux enterprise servers; configured IAM security roles and automated backup operations.
- Implemented system observability monitoring using Prometheus and Grafana dashboards for proactive alerting.

Key Projects
Multi-Cluster Kubernetes Deployment Platform
Technologies: Kubernetes, Docker, AWS, Terraform, CI/CD
- Deployed highly resilient container infrastructure with auto-scaling policies handling 25,000 requests per second.
- Secured infrastructure against vulnerabilities according to CIS benchmark standards.

Automated Disaster Recovery Infrastructure
Technologies: AWS, Terraform, Bash, Linux
- Scripted failover routines reducing Recovery Time Objective (RTO) from 4 hours to 12 minutes.

Education
Bachelor of Science in Computer Engineering
California State University, Long Beach (2016 - 2020)
"""
    create_pdf_resume(os.path.join(samples_dir, "sample_cloud_engineer.pdf"), cloud_engineer_text)

    # 5. Weak / Flawed Resume (DOCX) - missing email, missing projects, sparse skills, poor structure
    create_docx_resume(
        os.path.join(samples_dir, "sample_weak_resume.docx"),
        title_name="John",
        email="",  # Missing email!
        phone="555-1234",
        linkedin="",  # Missing LinkedIn!
        github="",    # Missing GitHub!
        summary="Looking for a job in technology.",
        skills=["Computers", "Microsoft Office", "Problem Solving"],
        experience=[
            {
                "role": "Helper",
                "company": "Local Shop",
                "dates": "2023",
                "bullets": [
                    "Helped with various computer tasks and assisted customers."
                ]
            }
        ],
        projects=[],  # No projects!
        education=[
            {"degree": "High School Diploma", "school": "Central High", "dates": "2022"}
        ]
    )

    print("All sample resumes generated successfully!")


if __name__ == "__main__":
    main()
