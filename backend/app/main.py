"""
CareerOS - AI Career Operating System
Main FastAPI application with modular architecture.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import os
import io
import re
import urllib.parse
from dotenv import load_dotenv

# PDF parsing
try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import PyPDF2
        PDF_LIBRARY = "PyPDF2"
    except ImportError:
        PDF_LIBRARY = None

# Load environment variables
load_dotenv()

# Import our modules
from app.models.schemas import (
    SearchFilters, ResumeData, JobListing, ScoredJob, JobIntelligence,
    MatchExplanation, LearningResource, CertificationRecommendation,
    ROIAction, CareerRoadmap, CareerDashboard, JobDetails,
    RecommendationResponse, InternshipBase, InternshipCreate, Internship,
    InternshipUpdate,
)
from app.scrapers.registry import search_all_platforms, list_scrapers, clear_cache, platform_status
from app.services.query_generator import infer_target_roles, generate_search_queries
from app.services.job_intelligence import score_jobs, score_job
from app.services.learning_engine import recommend_courses, recommend_certifications, calculate_roi_actions
from app.services.career_roadmap import generate_roadmap
from app.services.career_dashboard import generate_dashboard
from app.services.hiring_probability import enhance_intelligence
from app.services.certification_engine import discover_certifications, get_certification_providers, get_certification_categories
from app.services.search_streamer import stream_search_progress

# ─────────────────────────── App Setup ───────────────────────────

app = FastAPI(
    title="CareerOS - AI Career Operating System",
    description="AI-powered career intelligence platform. Upload your resume, discover fresh opportunities, and accelerate your career.",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
internships_db: Dict[str, Any] = {}

# ─────────────────────────── NVIDIA NIM Client ───────────────────────────

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

nvim_client = None
if NVIDIA_API_KEY:
    try:
        from openai import OpenAI
        nvim_client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
    except Exception:
        nvim_client = None

# ─────────────────────────── PDF Parsing ───────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file using available library."""
    if PDF_LIBRARY == "pdfplumber":
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    elif PDF_LIBRARY == "PyPDF2":
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    else:
        raise HTTPException(status_code=500, detail="No PDF parsing library installed.")

# ─────────────────────────── Resume Parsing ───────────────────────────

SKILL_PATTERNS = [
    "python", "javascript", "typescript", "java", "c\\\\+\\\\+", "react", "angular",
    "vue", "node\\\\.?js", "express", "django", "flask", "fastapi", "sql", "mongodb",
    "postgresql", "mysql", "aws", "azure", "gcp", "docker", "kubernetes", "git",
    "html", "css", "tailwind", "bootstrap", "figma", "photoshop", "illustrator",
    "machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "data science",
    "excel", "powerpoint", "word", "premiere", "after effects",
    "solidity", "blockchain", "web3", "react native", "flutter", "swift", "kotlin",
    "rust", "go", "ruby", "php", "laravel", "spring", "dotnet", "c#",
    "linux", "bash", "powershell", "jenkins", "ci/cd", "terraform", "ansible",
    "agile", "scrum", "jira", "confluence", "slack", "notion",
    "communication", "leadership", "teamwork", "problem solving", "analytical",
    "next.js", "redux", "graphql", "rest api", "grpc", "kafka", "redis",
    "elasticsearch", "spark", "hadoop", "airflow", "dbt", "snowflake",
    "tableau", "power bi", "looker", "scala", "r", "matlab", "sas",
    "penetration testing", "cybersecurity", "networking", "dns", "tcp/ip",
    "ux design", "user research", "wireframing", "prototyping",
]


def parse_resume(text: str) -> ResumeData:
    """Parse resume text to extract skills, experience, education, and projects."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Extract skills
    text_lower = text.lower()
    found_skills = []
    for skill in SKILL_PATTERNS:
        if re.search(r'\b' + skill + r'\b', text_lower):
            clean_skill = skill.replace("\\+\\+", "++").replace("\\.\\?", ".").replace("\\b", "")
            found_skills.append(clean_skill.title() if len(clean_skill) > 3 else clean_skill.upper())

    # Extract education
    education_keywords = ["bachelor", "master", "phd", "b.sc", "m.sc", "b.tech", "m.tech",
                         "bca", "mca", "bba", "mba", "degree", "university", "college",
                         "institute", "school"]
    education = []
    for line in lines:
        if any(kw in line.lower() for kw in education_keywords):
            education.append(line[:120])

    # Extract experience
    exp_keywords = ["experience", "worked", "intern", "developer", "engineer", "analyst",
                   "manager", "lead", "senior", "junior", "freelance"]
    experience = []
    for line in lines:
        if any(kw in line.lower() for kw in exp_keywords):
            experience.append(line[:120])

    # Extract projects
    project_keywords = ["project", "built", "developed", "created", "implemented", "designed"]
    projects = []
    for line in lines:
        if any(kw in line.lower() for kw in project_keywords):
            projects.append(line[:120])

    # Estimate years of experience
    years = 0.0
    for line in lines:
        m = re.search(r'(\d+)\s*(?:\+?\s*)?(?:years?|yrs?)', line.lower())
        if m:
            years = max(years, float(m.group(1)))

    # Build summary
    summary_lines = [l for l in lines[:15] if len(l) > 10][:5]
    summary = " | ".join(summary_lines) if summary_lines else "Resume parsed successfully"

    resume_data = ResumeData(
        text=text[:2000],
        skills=list(set(found_skills[:25])),
        experience=experience[:5],
        education=education[:3],
        projects=projects[:5],
        summary=summary,
        years_experience=years,
    )

    # Infer target roles
    resume_data.target_roles = infer_target_roles(resume_data)

    return resume_data


# ─────────────────────────── AI Suggestion Engine ───────────────────────────

async def get_ai_suggestions(resume: ResumeData, scored_jobs: List[ScoredJob]) -> str:
    """Get AI-powered career suggestions."""
    skill_text = ", ".join(resume.skills[:10]) if resume.skills else "general"
    role_text = ", ".join(resume.target_roles[:3]) if resume.target_roles else "various"

    # Build context from scored jobs
    top_jobs = scored_jobs[:3]
    job_context = ""
    for sj in top_jobs:
        job_context += f"\n- {sj.job.title} at {sj.job.company} (Match: {sj.intelligence.overall_match_pct}%)"

    prompt = f"""You are an expert career advisor. Analyze this profile and provide actionable advice:

Profile:
- Skills: {skill_text}
- Target Roles: {role_text}
- Experience: {resume.years_experience or 'entry-level'}
- Education: {'; '.join(resume.education[:2]) if resume.education else 'student'}

Top Matching Jobs:{job_context}

Provide 5 specific, actionable recommendations:
1. Best roles to apply for (with reasoning)
2. Top 3 companies to target
3. Skills to highlight on resume
4. Critical skills to learn next (with estimated time)
5. One strategic career move

Be specific and practical. Format as numbered list."""

    if nvim_client:
        try:
            completion = nvim_client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a senior career advisor specializing in tech careers. Be specific, actionable, and encouraging."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=600,
            )
            return completion.choices[0].message.content
        except Exception:
            pass

    # Fallback suggestions
    suggestions = []
    if resume.target_roles:
        suggestions.append(f"🎯 **Target roles**: {', '.join(resume.target_roles[:3])}")
    if resume.skills:
        suggestions.append(f"💪 **Highlight**: {', '.join(resume.skills[:5])}")
    if scored_jobs:
        best = scored_jobs[0]
        suggestions.append(f"🏆 **Best match**: {best.job.title} at {best.job.company} ({best.intelligence.overall_match_pct}% match)")

    suggestions.append("📋 **Tip**: Tailor your resume for each application, emphasizing relevant skills")
    suggestions.append("🚀 **Action**: Apply to 5-10 positions this week for best results")

    return "\n".join(suggestions)


# ─────────────────────────── API Routes ───────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "CareerOS - AI Career Operating System",
        "version": "4.0.0",
        "endpoints": {
            "recommendations": "POST /api/recommendations",
            "upload_resume": "POST /api/upload-resume",
            "job_details": "POST /api/job-details",
            "dashboard": "POST /api/dashboard",
            "learning": "POST /api/learning",
            "roadmap": "POST /api/roadmap",
            "platforms": "GET /api/platforms",
            "health": "GET /api/health",
            "cache_clear": "POST /api/cache/clear",
        },
        "platforms": list_scrapers(),
        "platform_count": len(list_scrapers()),
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "4.0.0",
        "pdf_library": PDF_LIBRARY,
        "nvidia_configured": nvim_client is not None,
        "platforms": list_scrapers(),
        "platform_count": len(list_scrapers()),
        "platform_status": platform_status,
    }


@app.get("/api/platforms", tags=["Platforms"])
async def get_platforms():
    """List all available job platforms."""
    return {
        "platforms": list_scrapers(),
        "count": len(list_scrapers()),
        "platform_status": platform_status,
    }


@app.post("/api/cache/clear", tags=["Cache"])
async def clear_search_cache():
    """Clear all cached search results."""
    clear_cache()
    return {"success": True, "message": "Cache cleared"}


# ──────────── Resume Upload ────────────

@app.post("/api/upload-resume", tags=["Resume"])
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    text = extract_text_from_pdf(contents)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    resume_data = parse_resume(text)
    return {"success": True, "filename": file.filename, "resume_data": resume_data}


# ──────────── Main Recommendations Endpoint ────────────

@app.post("/api/recommendations", response_model=RecommendationResponse, tags=["Recommendations"])
async def get_recommendations(
    file: UploadFile = File(...),
    location: str = Form(default=""),
    job_type: str = Form(default="both"),
    work_style: str = Form(default="any"),
    experience_level: str = Form(default="0-1"),
    preferred_tech: str = Form(default=""),
    recency: str = Form(default="week"),
    sort_by: str = Form(default="newest"),
    include_old: bool = Form(default=False),
    easy_apply_only: bool = Form(default=False),
    faang_only: bool = Form(default=False),
    startups_only: bool = Form(default=False),
):
    """
    Full career intelligence pipeline:
    1. Parse resume → extract skills, experience, education
    2. Generate smart search queries from resume (role-based, never raw skills)
    3. Search 12 platforms concurrently with recency sorting
    4. Deduplicate and merge duplicate jobs across platforms
    5. Score and rank all jobs with intelligence
    6. Generate learning recommendations
    7. Calculate ROI actions
    8. Build career roadmap
    9. Generate dashboard metrics
    """
    # 1. Parse resume
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    text = extract_text_from_pdf(contents)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    resume = parse_resume(text)

    # 2. Build search filters with recency
    tech_list = [t.strip() for t in preferred_tech.split(",") if t.strip()] if preferred_tech else []
    filters = SearchFilters(
        job_type=job_type,
        work_style=work_style,
        city=location,
        country="India",
        experience_level=experience_level,
        preferred_tech=tech_list,
        recency=recency,
        sort_by=sort_by,
        include_old=include_old,
        easy_apply_only=easy_apply_only,
        faang_only=faang_only,
        startups_only=startups_only,
    )

    # 3. Search all 12 platforms concurrently
    all_jobs, sources_searched, plat_status = await search_all_platforms(resume.skills, filters)

    # 4. Score and rank all jobs
    scored_jobs = score_jobs(all_jobs, resume, filters)

    # Sort by selected criteria (uses _sort_scored_jobs helper)
    scored_jobs = _sort_scored_jobs(scored_jobs, sort_by)

    # 5. Generate learning recommendations
    all_missing = []
    for sj in scored_jobs:
        all_missing.extend(sj.intelligence.match_explanation.missing_skills)
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(10)]

    learning = recommend_courses(top_missing, resume.skills)
    certifications = recommend_certifications(top_missing, resume.skills)

    # 6. Calculate ROI actions
    roi_actions = calculate_roi_actions(top_missing, resume.skills, certifications)

    # 7. Build career roadmap
    roadmap = generate_roadmap(resume, top_missing, learning, certifications, roi_actions)

    # 8. Generate dashboard
    dashboard = generate_dashboard(
        resume,
        [sj.intelligence for sj in scored_jobs],
        learning,
        roi_actions,
        roadmap,
    )

    # 9. Discover certifications from the full catalog
    cert_discovery = discover_certifications(resume.skills, resume)

    # 10. Get AI suggestions
    ai_suggestions = await get_ai_suggestions(resume, scored_jobs)

    # 11. Build discovery metadata
    by_platform = {}
    by_type = {"internship": 0, "full-time": 0, "contract": 0, "other": 0}
    by_recency = {"today": 0, "24h": 0, "3days": 0, "week": 0, "month": 0, "older": 0}

    for sj in scored_jobs:
        src = sj.job.source
        by_platform[src] = by_platform.get(src, 0) + 1

        et = sj.job.employment_type
        if et in by_type:
            by_type[et] += 1
        else:
            by_type["other"] += 1

        # Recency buckets
        fs = sj.job.freshness_score
        if fs >= 95:
            by_recency["today"] += 1
        elif fs >= 90:
            by_recency["24h"] += 1
        elif fs >= 70:
            by_recency["3days"] += 1
        elif fs >= 50:
            by_recency["week"] += 1
        elif fs >= 20:
            by_recency["month"] += 1
        else:
            by_recency["older"] += 1

    return RecommendationResponse(
        resume_data=resume,
        jobs=scored_jobs[:100],  # Top 100 jobs to ensure 50+ survive dedup and filtering
        ai_suggestions=ai_suggestions,
        sources_searched=sources_searched,
        search_filters=filters,
        learning=learning,
        certifications=certifications,
        roi_actions=roi_actions,
        career_roadmap=roadmap,
        dashboard=dashboard,
        total_found=len(scored_jobs),
        by_platform=by_platform,
        by_type=by_type,
        by_recency=by_recency,
        platform_status=plat_status,
        certification_discovery=cert_discovery[:10],
    )


# ──────────── Job Details Endpoint (JSON) ────────────

class JobDetailsRequest(BaseModel):
    resume_text: str = ""
    job_title: str
    job_company: str
    job_location: str = ""
    job_description: str = ""
    job_apply_link: str = ""

@app.post("/api/job-details-json", tags=["Job Details"])
async def get_job_details_json(req: JobDetailsRequest):
    """Get detailed analysis for a specific job using previously parsed resume text."""
    resume = parse_resume(req.resume_text) if req.resume_text else ResumeData()

    job = JobListing(
        title=req.job_title,
        company=req.job_company,
        location=req.job_location,
        description=req.job_description,
        apply_link=req.job_apply_link,
        source="manual",
    )

    scored = score_job(job, resume)

    resume_suggestions = []
    if scored.intelligence.match_explanation.missing_skills:
        resume_suggestions.append(f"Add projects demonstrating {', '.join(scored.intelligence.match_explanation.missing_skills[:3])}")
    if scored.intelligence.match_explanation.matched_skills:
        resume_suggestions.append(f"Highlight your experience with {', '.join(scored.intelligence.match_explanation.matched_skills[:3])}")
    resume_suggestions.append("Quantify achievements with specific numbers and metrics")
    resume_suggestions.append("Tailor your summary to match this role's requirements")

    likely_questions = _generate_interview_questions(job, resume.skills)
    ai_rec = await _generate_job_recommendation(job, resume, scored.intelligence)

    return JobDetails(
        job=job,
        intelligence=scored.intelligence,
        resume_suggestions=resume_suggestions,
        interview_difficulty=scored.intelligence.difficulty,
        likely_questions=likely_questions,
        company_research=f"Research {job.company} on Glassdoor, LinkedIn, and their careers page",
        tech_stack=scored.intelligence.match_explanation.matched_skills,
        hiring_process="Typically: Application → Phone Screen → Technical Interview → Final Round",
        ai_recommendation=ai_rec,
    )

# ──────────── Job Details Endpoint (Legacy file upload) ────────────

@app.post("/api/job-details", tags=["Job Details"])
async def get_job_details(
    file: UploadFile = File(...),
    job_title: str = Form(...),
    job_company: str = Form(...),
    job_location: str = Form(default=""),
    job_description: str = Form(default=""),
    job_apply_link: str = Form(default=""),
):
    """Get detailed analysis for a specific job."""
    # Parse resume
    contents = await file.read()
    text = extract_text_from_pdf(contents)
    resume = parse_resume(text)

    # Create job listing
    job = JobListing(
        title=job_title,
        company=job_company,
        location=job_location,
        description=job_description,
        apply_link=job_apply_link,
        source="manual",
    )

    # Score it
    scored = score_job(job, resume)

    # Generate detailed analysis
    resume_suggestions = []
    if scored.intelligence.match_explanation.missing_skills:
        resume_suggestions.append(f"Add projects demonstrating {', '.join(scored.intelligence.match_explanation.missing_skills[:3])}")
    if scored.intelligence.match_explanation.matched_skills:
        resume_suggestions.append(f"Highlight your experience with {', '.join(scored.intelligence.match_explanation.matched_skills[:3])}")
    resume_suggestions.append("Quantify achievements with specific numbers and metrics")
    resume_suggestions.append("Tailor your summary to match this role's requirements")

    likely_questions = _generate_interview_questions(job, resume.skills)

    # AI recommendation
    ai_rec = await _generate_job_recommendation(job, resume, scored.intelligence)

    return JobDetails(
        job=job,
        intelligence=scored.intelligence,
        resume_suggestions=resume_suggestions,
        interview_difficulty=scored.intelligence.difficulty,
        likely_questions=likely_questions,
        company_research=f"Research {job.company} on Glassdoor, LinkedIn, and their careers page",
        tech_stack=scored.intelligence.match_explanation.matched_skills,
        hiring_process="Typically: Application → Phone Screen → Technical Interview → Final Round",
        ai_recommendation=ai_rec,
    )


def _generate_interview_questions(job: JobListing, skills: List[str]) -> List[str]:
    """Generate likely interview questions based on job and skills."""
    questions = []

    if any(s.lower() in job.title.lower() for s in ["frontend", "react", "ui"]):
        questions.extend([
            "Explain the React virtual DOM and reconciliation process",
            "How do you optimize React component performance?",
            "Describe your experience with state management (Redux, Context, Zustand)",
        ])
    elif any(s.lower() in job.title.lower() for s in ["backend", "api", "server"]):
        questions.extend([
            "Design a RESTful API for this use case",
            "How do you handle authentication and authorization?",
            "Explain database indexing and query optimization",
        ])
    elif any(s.lower() in job.title.lower() for s in ["ml", "data", "ai"]):
        questions.extend([
            "Explain overfitting and how to prevent it",
            "Describe your experience with model deployment",
            "How do you handle imbalanced datasets?",
        ])
    else:
        questions.extend([
            "Tell me about a challenging project you've worked on",
            "How do you approach debugging complex issues?",
            "Describe your experience working in a team environment",
        ])

    questions.append("Why are you interested in this role at this company?")
    return questions[:5]


async def _generate_job_recommendation(job: JobListing, resume: ResumeData, intelligence: JobIntelligence) -> str:
    """Generate AI recommendation for a specific job."""
    if nvim_client:
        try:
            prompt = f"""Analyze this job match and provide a recommendation:

Job: {job.title} at {job.company}
Location: {job.location}
Match Score: {intelligence.overall_match_pct}%
Skills Match: {intelligence.skill_match_pct}%
User Skills: {', '.join(resume.skills[:8])}
Missing Skills: {', '.join(intelligence.match_explanation.missing_skills[:5])}

Should the user apply? What should they emphasize? Be specific."""
            completion = nvim_client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a career advisor. Be concise and actionable."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            return completion.choices[0].message.content
        except Exception:
            pass

    # Fallback
    if intelligence.overall_match_pct > 70:
        return f"Strong match ({intelligence.overall_match_pct}%)! Apply and emphasize your {', '.join(intelligence.match_explanation.matched_skills[:3])} experience."
    elif intelligence.overall_match_pct > 40:
        return f"Decent match ({intelligence.overall_match_pct}%). Consider learning {', '.join(intelligence.match_explanation.missing_skills[:2])} before applying, or apply anyway if interested."
    else:
        return f"Lower match ({intelligence.overall_match_pct}%). This role requires skills you're still developing. Great learning opportunity if you want to grow in this direction."


# ──────────── Dashboard Endpoint ────────────

@app.post("/api/dashboard", tags=["Dashboard"])
async def get_dashboard(file: UploadFile = File(...)):
    """Generate career dashboard metrics."""
    contents = await file.read()
    text = extract_text_from_pdf(contents)
    resume = parse_resume(text)

    # Search for context
    all_jobs, sources, _ = await search_all_platforms(resume.skills)
    scored_jobs = score_jobs(all_jobs, resume)

    all_missing = []
    for sj in scored_jobs:
        all_missing.extend(sj.intelligence.match_explanation.missing_skills)
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(10)]

    learning = recommend_courses(top_missing, resume.skills)
    certifications = recommend_certifications(top_missing, resume.skills)
    roi_actions = calculate_roi_actions(top_missing, resume.skills, certifications)
    roadmap = generate_roadmap(resume, top_missing, learning, certifications, roi_actions)

    dashboard = generate_dashboard(
        resume,
        [sj.intelligence for sj in scored_jobs],
        learning,
        roi_actions,
        roadmap,
    )

    return dashboard


# ──────────── Learning Endpoint ────────────

@app.post("/api/learning", tags=["Learning"])
async def get_learning_recommendations(file: UploadFile = File(...)):
    """Get personalized learning recommendations."""
    contents = await file.read()
    text = extract_text_from_pdf(contents)
    resume = parse_resume(text)

    all_jobs, _, _ = await search_all_platforms(resume.skills)
    scored_jobs = score_jobs(all_jobs, resume)

    all_missing = []
    for sj in scored_jobs:
        all_missing.extend(sj.intelligence.match_explanation.missing_skills)
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(10)]

    learning = recommend_courses(top_missing, resume.skills)
    certifications = recommend_certifications(top_missing, resume.skills)

    return {
        "learning": learning,
        "certifications": certifications,
        "missing_skills": top_missing,
    }


# ──────────── Roadmap Endpoint ────────────

@app.post("/api/roadmap", tags=["Roadmap"])
async def get_career_roadmap(file: UploadFile = File(...)):
    """Generate a 30/60/90 day career roadmap."""
    contents = await file.read()
    text = extract_text_from_pdf(contents)
    resume = parse_resume(text)

    all_jobs, _, _ = await search_all_platforms(resume.skills)
    scored_jobs = score_jobs(all_jobs, resume)

    all_missing = []
    for sj in scored_jobs:
        all_missing.extend(sj.intelligence.match_explanation.missing_skills)
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(10)]

    learning = recommend_courses(top_missing, resume.skills)
    certifications = recommend_certifications(top_missing, resume.skills)
    roi_actions = calculate_roi_actions(top_missing, resume.skills, certifications)
    roadmap = generate_roadmap(resume, top_missing, learning, certifications, roi_actions)

    return roadmap


# ──────────── Legacy Endpoints (backward compatible) ────────────

@app.get("/api/recommendations/{user_id}", tags=["Recommendations"])
async def get_recommendations_legacy(user_id: str):
    """Legacy endpoint - use POST /api/recommendations instead."""
    return {
        "message": "Use POST /api/recommendations with a resume PDF for personalized career intelligence.",
        "endpoint": "POST /api/recommendations",
    }


# ──────────── Internship CRUD ────────────

@app.post("/api/internships", response_model=Internship, status_code=status.HTTP_201_CREATED, tags=["Internships"])
async def create_internship(internship: InternshipCreate):
    internship_obj = Internship(**internship.model_dump())
    internships_db[internship_obj.id] = internship_obj
    return internship_obj


@app.get("/api/internships", response_model=List[Internship], tags=["Internships"])
async def list_internships(skip: int = 0, limit: int = 100):
    return list(internships_db.values())[skip:skip+limit]


@app.get("/api/internships/{internship_id}", response_model=Internship, tags=["Internships"])
async def get_internship(internship_id: str):
    internship = internships_db.get(internship_id)
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")
    return internship


@app.put("/api/internships/{internship_id}", response_model=Internship, tags=["Internships"])
async def update_internship(internship_id: str, internship_update: InternshipUpdate):
    stored = internships_db.get(internship_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Internship not found")
    update_data = internship_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stored, field, value)
    internships_db[internship_id] = stored
    return stored


@app.delete("/api/internships/{internship_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Internships"])
async def delete_internship(internship_id: str):
    if internship_id not in internships_db:
        raise HTTPException(status_code=404, detail="Internship not found")
    del internships_db[internship_id]
    return None


# ──────────── V2: Certification Discovery Endpoint ────────────

class CertDiscoveryRequest(BaseModel):
    skills: List[str] = []
    category: Optional[str] = None
    free_only: bool = False

@app.post("/api/certifications/discover", tags=["Certifications"])
async def discover_certifications_endpoint(req: CertDiscoveryRequest):
    """Discover certifications relevant to user's skills."""
    certs = discover_certifications(req.skills, category=req.category, free_only=req.free_only)
    return {
        "certifications": certs,
        "total": len(certs),
        "providers": get_certification_providers(),
        "categories": get_certification_categories(),
    }


@app.get("/api/certifications/providers", tags=["Certifications"])
async def get_cert_providers():
    """List all certification providers."""
    return {"providers": get_certification_providers(), "categories": get_certification_categories()}


# ──────────── V2: SSE Streaming Search Endpoint ────────────

from fastapi.responses import StreamingResponse

class StreamingSearchRequest(BaseModel):
    skills: List[str] = []
    recency: str = "week"
    sort_by: str = "newest"
    job_type: str = "both"
    work_style: str = "any"
    experience_level: str = "0-1"
    city: str = ""
    easy_apply_only: bool = False
    faang_only: bool = False
    startups_only: bool = False

@app.post("/api/search/stream", tags=["Search"])
async def stream_search(req: StreamingSearchRequest):
    """Stream search progress via SSE."""
    filters = SearchFilters(
        job_type=req.job_type,
        work_style=req.work_style,
        city=req.city,
        experience_level=req.experience_level,
        recency=req.recency,
        sort_by=req.sort_by,
    )
    return StreamingResponse(
        stream_search_progress(req.skills, filters),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────── V2: Sorting Helpers ────────────

FAANG_COMPANIES = [
    "google", "microsoft", "amazon", "apple", "meta", "netflix",
    "nvidia", "tesla", "salesforce", "adobe", "oracle",
    "uber", "airbnb", "spotify", "databricks", "snowflake",
    "stripe", "cloudflare", "vercel", "notion", "anthropic",
    "openai", "deepmind", "bytedance", "shopify",
]

def _sort_scored_jobs(scored_jobs, sort_by: str):
    """Sort scored jobs by the specified criteria."""
    if sort_by == "newest":
        scored_jobs.sort(key=lambda s: s.job.freshness_score, reverse=True)
    elif sort_by == "match":
        scored_jobs.sort(key=lambda s: s.intelligence.overall_match_pct, reverse=True)
    elif sort_by == "salary":
        scored_jobs.sort(key=lambda s: s.intelligence.salary_score, reverse=True)
    elif sort_by == "faang":
        def faang_key(s):
            is_faang = any(c in s.job.company.lower() for c in FAANG_COMPANIES)
            return (is_faang, s.intelligence.overall_match_pct)
        scored_jobs.sort(key=faang_key, reverse=True)
    elif sort_by == "startups":
        def startup_key(s):
            is_startup = any(k in s.job.description.lower() or k in s.job.company.lower()
                          for k in ["startup", "seed", "series", "yc", "early stage"])
            return (is_startup, s.intelligence.overall_match_pct)
        scored_jobs.sort(key=startup_key, reverse=True)
    elif sort_by == "easy_apply":
        scored_jobs.sort(key=lambda s: (s.intelligence.overall_match_pct), reverse=True)
    else:
        scored_jobs.sort(key=lambda s: s.intelligence.overall_match_pct, reverse=True)
    return scored_jobs
