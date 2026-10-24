"""
Generates realistic sample resumes in both PDF and DOCX formats for testing and academic demonstrations.
Includes calibrated word counts reflecting authentic industry distributions:
- Strong profiles (420-480 words): Rich project architecture, metrics, and experience
- Sparse profiles (~200 words): Short descriptions lacking technical depth
- Weak profiles (~40 words): Missing contact, missing sections, and severe deficiencies
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
    rect = pymupdf.Rect(40, 40, 560, 800)
    page.insert_textbox(rect, text_content, fontsize=9.5, fontname="helv")
    doc.save(filepath)
    doc.close()
    print(f"Generated PDF: {filepath}")


def main():
    samples_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. AI Engineer Sample (DOCX) - Realistic 460-word Strong Profile
    create_docx_resume(
        os.path.join(samples_dir, "sample_ai_engineer.docx"),
        title_name="Alex Chen",
        email="alex.chen.ai@example.com",
        phone="+1 (555) 234-5678",
        linkedin="https://linkedin.com/in/alexchen-ai",
        github="https://github.com/alexchen-ml",
        summary="Results-driven AI and Machine Learning Engineer with 3+ years of experience designing, evaluating, and deploying production-grade deep learning architectures, transformer pipelines, and computer vision systems. Proven track record of optimizing model inference latency, automating scalable data preprocessing pipelines, and collaborating with cross-functional software teams to integrate ML models into enterprise microservices.",
        skills=["Python", "PyTorch", "TensorFlow", "scikit-learn", "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Docker", "Pandas", "NumPy", "Hugging Face", "Transformers", "OpenCV", "Feature Engineering", "Data Preprocessing", "MLOps"],
        experience=[
            {
                "role": "Machine Learning Engineer",
                "company": "Cognitive Solutions Inc.",
                "dates": "2022 - Present",
                "bullets": [
                    "Architected and deployed production deep learning models using PyTorch and Hugging Face Transformers, improving inference throughput by 35% across 400,000 daily user requests.",
                    "Automated end-to-end data preprocessing and feature engineering pipelines for 10TB of unstructured text datasets, reducing pipeline runtime by 42%.",
                    "Collaborated with backend engineering teams to containerize model inference servers using Docker and Kubernetes, maintaining 99.95% API uptime availability.",
                    "Conducted rigorous offline evaluation, A/B testing, and error analysis, reducing model hallucination rates by 24% on validation benchmarks."
                ]
            },
            {
                "role": "AI Research & Development Intern",
                "company": "DeepTech Labs",
                "dates": "2021 - 2022",
                "bullets": [
                    "Engineered real-time computer vision detection algorithms with OpenCV and TensorFlow, achieving 94.2% mean Average Precision (mAP) on edge devices.",
                    "Implemented distributed training workflows across multi-GPU clusters, accelerating model experimentation cycles by 2.5x.",
                    "Documented experimental findings, published technical reports, and presented prototype demonstrations to senior stakeholders."
                ]
            }
        ],
        projects=[
            {
                "name": "Neural Semantic Search & Retrieval Engine",
                "tech": "PyTorch, Transformers, Hugging Face, Docker, FastAPI",
                "bullets": [
                    "Engineered a high-throughput semantic vector search retrieval engine indexing 2.5 million documents with sub-65ms p95 query latency.",
                    "Fine-tuned bi-encoder and cross-encoder transformer architectures, yielding a 22% improvement in Mean Reciprocal Rank (MRR) over keyword search baselines.",
                    "Containerized the FastAPI inference service with Docker and orchestrated deployment via CI/CD pipelines."
                ]
            },
            {
                "name": "Automated Medical Diagnostic Image Classifier",
                "tech": "TensorFlow, scikit-learn, OpenCV, Python",
                "bullets": [
                    "Trained convolutional neural networks (CNNs) using transfer learning on 35,000 radiological scans, achieving 96.1% diagnostic sensitivity.",
                    "Applied data augmentation and feature attribution heatmaps (Grad-CAM) to provide explainable model predictions for clinicians."
                ]
            }
        ],
        education=[
            {"degree": "Master of Science in Computer Science (Artificial Intelligence Specialization)", "school": "State University Institute of Technology", "dates": "2020 - 2022"},
            {"degree": "Bachelor of Technology in Computer Engineering", "school": "National Institute of Technology", "dates": "2016 - 2020"}
        ]
    )

    # 2. Web Developer Sample (DOCX) - Realistic 440-word Strong Profile
    create_docx_resume(
        os.path.join(samples_dir, "sample_web_developer.docx"),
        title_name="Sarah Miller",
        email="sarah.miller.dev@example.com",
        phone="+1 415-555-0199",
        linkedin="https://linkedin.com/in/sarahmiller-dev",
        github="https://github.com/sarahmiller-web",
        summary="Innovative Full Stack Web Developer with 3+ years of professional experience architecting, implementing, and maintaining high-volume web applications. Expert in modern JavaScript and TypeScript ecosystems, React component architectures, Node.js backend services, and relational/NoSQL database management. Committed to writing clean, modular code adhering to accessibility and performance standards.",
        skills=["JavaScript", "TypeScript", "React", "Node.js", "Express", "HTML5", "CSS3", "Git", "REST API", "MongoDB", "PostgreSQL", "Responsive Design", "Bootstrap", "Tailwind CSS", "Docker", "GraphQL"],
        experience=[
            {
                "role": "Full Stack Web Developer",
                "company": "PixelCraft Studios",
                "dates": "2021 - Present",
                "bullets": [
                    "Architected and deployed responsive single-page web applications using React, TypeScript, and Node.js serving over 250,000 monthly active users.",
                    "Engineered robust RESTful API endpoints and GraphQL microservices with Express and PostgreSQL, reducing endpoint response latency by 28%.",
                    "Implemented Redux state management patterns and optimized component re-rendering cycles, boosting Google Lighthouse performance scores from 72 to 96.",
                    "Conducted peer code reviews, mentored 3 junior developers, and maintained 90%+ unit test coverage using Jest and React Testing Library."
                ]
            },
            {
                "role": "Frontend Developer Intern",
                "company": "Nexus Web Solutions",
                "dates": "2020 - 2021",
                "bullets": [
                    "Developed accessible, cross-browser responsive interfaces with HTML5, CSS3, and JavaScript adhering strictly to WCAG 2.1 accessibility guidelines.",
                    "Collaborated with UX designers in Figma to translate wireframes into reusable, maintainable React component libraries.",
                    "Standardized team Git branching strategies and automated pull request preview deployments via CI/CD workflows."
                ]
            }
        ],
        projects=[
            {
                "name": "E-Commerce Multi-Vendor Marketplace Platform",
                "tech": "React, Node.js, Express, MongoDB, REST API, Stripe",
                "bullets": [
                    "Constructed an enterprise-grade e-commerce application processing $1.8M in annual recurring transactions with zero downtime.",
                    "Implemented secure JWT authentication, role-based access control (RBAC), and transactional email notifications.",
                    "Designed dynamic inventory search filters and caching layers using Redis, decreasing database load by 40%."
                ]
            },
            {
                "name": "Real-Time Collaborative Team Workspace",
                "tech": "TypeScript, React, PostgreSQL, WebSocket, Docker",
                "bullets": [
                    "Built real-time collaborative whiteboard and task board application supporting concurrent multi-user editing with sub-50ms synchronization.",
                    "Containerized full-stack application with Docker Compose for seamless developer onboarding and staging deployments."
                ]
            }
        ],
        education=[
            {"degree": "Bachelor of Science in Information Technology and Web Engineering", "school": "Metropolitan College University", "dates": "2017 - 2021"}
        ]
    )

    # 3. Data Analyst Sample (PDF) - Realistic 450-word Strong Profile
    data_analyst_text = """Maya Patel
maya.patel.analytics@example.com | +1 (650) 555-0143
https://linkedin.com/in/mayapatel-data | https://github.com/mayapatel-analytics

Professional Summary
Detail-oriented and commercially driven Data Analyst with 3+ years of experience transforming complex multi-source datasets into strategic business intelligence and predictive models. Proven expertise in complex SQL database querying, statistical hypothesis testing in Python, automated ETL pipeline design, and interactive executive KPI dashboard development using Power BI and Tableau. Skilled in stakeholder communication, translating quantitative trends into actionable commercial decisions that maximize revenue growth and operational efficiency.

Technical Skills
SQL, Python, Excel, Pandas, NumPy, Power BI, Tableau, Data Visualization, Statistics, ETL, Data Cleaning, Data Modeling, A/B Testing, Business Intelligence, Matplotlib, Seaborn, Relational Databases, Regression Analysis

Work Experience
Senior Data Analyst - Retail Insights Corp (2022 - Present)
- Formulated complex SQL queries and window functions across relational databases comprising 20M+ records to evaluate customer retention cohorts, increasing customer lifetime value (LTV) by 16%.
- Designed and automated 12+ executive KPI dashboards in Power BI and Tableau utilized daily by C-suite executives for operational forecasting and inventory allocation.
- Led A/B testing experiments on dynamic promotional pricing algorithms, resulting in an annualized $420,000 increase in gross retail margin.
- Standardized data hygiene protocols across data warehouse pipelines, eliminating duplicate records and reducing reporting anomalies by 35%.

Data Analyst - FinMetrics Global (2021 - 2022)
- Built automated ETL data cleaning scripts using Python, Pandas, and NumPy, reducing manual data compilation time by 18 hours per business week.
- Performed statistical regression and cohort analysis to identify leading indicators of customer churn, presenting slide deck insights directly to divisional heads.
- Automated daily financial reconciliation reports in Excel using advanced VBA macros and Power Query connections.

Key Projects
Predictive Customer Churn & Lifetime Value Engine
Technologies: Python, SQL, Pandas, NumPy, Statistics, Scikit-learn
- Analyzed 850,000 customer transaction histories to train predictive logistic regression and random forest classification models.
- Identified high-risk attrition customer segments with 88% precision, enabling the retention marketing team to reduce churn by 14%.
- Published an interactive Tableau visualization portal communicating feature importance and risk distributions to non-technical business managers.

Omnichannel E-Commerce Conversion Optimization Dashboard
Technologies: Power BI, SQL, Data Modeling, Business Intelligence, Excel
- Centralized fragmented analytics across Google Analytics, internal ERP databases, and customer support ticketing into a unified star-schema data model.
- Identified multi-touch checkout funnel friction points, informing UX redesigns that boosted checkout conversion by 8.4%.

Education
Bachelor of Science in Statistics and Data Science (Magna Cum Laude)
University of Washington, Seattle (2017 - 2021)
"""
    create_pdf_resume(os.path.join(samples_dir, "sample_data_analyst.pdf"), data_analyst_text)

    # 4. Cloud Engineer Sample (PDF) - Realistic 450-word Strong Profile
    cloud_engineer_text = """Marcus Vance
marcus.vance.cloud@example.com | +1 (206) 555-8831
https://linkedin.com/in/marcusvance-cloud | https://github.com/marcusvance-ops

Professional Summary
Senior Cloud & DevOps Engineer specializing in scalable AWS cloud infrastructure architecture, Kubernetes container orchestration, Infrastructure as Code with Terraform, and zero-downtime automated CI/CD deployment pipelines. Experienced in managing Linux enterprise environments, designing fault-tolerant distributed networks, and implementing robust observability metrics using Prometheus and Grafana. Passionate about automated governance, cloud security compliance, and microservices scalability.

Technical Skills
AWS, Docker, Kubernetes, Linux, Terraform, CI/CD, Bash, Infrastructure as Code, Azure, Microservices, Prometheus, Grafana, Git, Networking, IAM, CloudFormation, Ansible, Python, System Administration

Work Experience
Senior Cloud Infrastructure Engineer - CloudScale Systems (2022 - Present)
- Architected and automated multi-region AWS cloud infrastructure using Terraform Infrastructure as Code (IaC), decreasing environment provisioning turnaround from 3 days to 25 minutes.
- Administered production Kubernetes (EKS) clusters hosting 60+ microservices handling 45,000 requests per second with 99.99% system availability.
- Built fully automated CI/CD deployment pipelines with Git and Bash, shortening sprint deployment cycles from bi-weekly releases to continuous daily deployments.
- Implemented enterprise IAM security baselines and role-based policies, achieving 100% compliance with SOC2 and CIS benchmark standards.

Linux Systems Administrator - Enterprise Cloud Net (2020 - 2022)
- Managed and maintained 150+ Red Hat Enterprise Linux (RHEL) server instances, configuring automated OS patching, system hardening, and storage backups.
- Deployed comprehensive infrastructure observability monitoring using Prometheus and Grafana, reducing Mean Time to Resolution (MTTR) by 45%.
- Scripted automated diagnostic routines using Bash and Python to detect server memory leaks and proactively prevent production outages.

Key Projects
Multi-Cluster Kubernetes Disaster Recovery & Scaling Platform
Technologies: Kubernetes, Docker, AWS, Terraform, CI/CD, Linux
- Deployed a fault-tolerant container orchestration platform across multiple AWS availability zones with automatic horizontal pod autoscaling (HPA).
- Automated disaster recovery failover routines, reducing Recovery Time Objective (RTO) from 4 hours to 8 minutes.
- Enforced zero-trust networking security policies and TLS termination across all internal service mesh communications.

Automated Cloud Migration & Compliance Framework
Technologies: AWS, Terraform, Ansible, Bash, IAM
- Successfully orchestrated the zero-downtime migration of on-premises legacy workloads into AWS EC2 and RDS environments.
- Implemented automated AWS Cost Explorer governance policies, optimizing reserved instance allocations to reduce monthly cloud expenditure by 28%.

Education
Bachelor of Science in Computer Engineering
California State University, Long Beach (2016 - 2020)
"""
    create_pdf_resume(os.path.join(samples_dir, "sample_cloud_engineer.pdf"), cloud_engineer_text)

    # 5. Weak / Flawed Resume (DOCX) - Intentionally Sparse 39-word Resume for Contrast Testing
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

    print("All sample resumes regenerated with calibrated realistic content!")


if __name__ == "__main__":
    main()
