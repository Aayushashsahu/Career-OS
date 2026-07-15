"""
CareerOS Data Models
All Pydantic schemas for the AI Career Operating System.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


# ─────────────────── Search Filters ───────────────────

class SearchFilters(BaseModel):
    """User preferences for job search."""
    job_type: str = "both"  # internship, full-time, both
    work_style: str = "any"  # remote, hybrid, on-site, any
    country: str = "India"
    city: str = ""
    state: str = ""
    radius_km: int = 50
    experience_level: str = "0-1"  # 0-1, 1-3, 3-5, 5+
    preferred_tech: List[str] = []
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    keywords: List[str] = []
    # Recency filters
    recency: str = "week"  # today, 24h, 3days, week, month, all
    sort_by: str = "newest"  # newest, match, relevance, salary, faang, startups, easy_apply
    include_old: bool = False  # If True, show jobs older than 14 days
    # V2: Additional filters
    easy_apply_only: bool = False  # Only show Easy Apply jobs
    faang_only: bool = False  # Only show FAANG/top-tier companies
    startups_only: bool = False  # Only show startup companies


# ─────────────────── Resume Models ───────────────────

class ResumeData(BaseModel):
    text: str = ""
    skills: List[str] = []
    experience: List[str] = []
    education: List[str] = []
    summary: str = ""
    target_roles: List[str] = []
    years_experience: float = 0.0
    projects: List[str] = []


# ─────────────────── Job Listing ───────────────────

class JobListing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    company: str
    location: str
    description: str = ""
    apply_link: str
    source: str
    stipend: Optional[str] = None
    salary: Optional[str] = None
    remote: bool = False
    employment_type: str = "internship"
    experience_required: str = ""
    skills_required: List[str] = []
    skills_found: List[str] = []
    skills_missing: List[str] = []
    posted_date: str = ""
    company_logo: str = ""
    # Freshness & dedup fields
    posted_timestamp: Optional[float] = None  # Unix timestamp for sorting
    freshness_score: float = 0.0  # 0-100, how fresh (100 = today)
    freshness_badge: str = ""  # "Today", "2 days ago", "This week", etc.
    dedup_key: str = ""  # Normalized key for dedup: title+company+location
    work_style: str = "on-site"  # remote, hybrid, on-site
    company_url: str = ""
    # Source tracking for dedup
    sources: List[str] = []  # All platforms where this job was found
    apply_urls: Dict[str, str] = {}  # platform -> URL mapping


# ─────────────────── Intelligence Scores ───────────────────

class MatchExplanation(BaseModel):
    """WHY a job matches or doesn't match."""
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    experience_match: str = ""
    location_match: str = ""
    reasons_for: List[str] = []
    reasons_against: List[str] = []


class JobIntelligence(BaseModel):
    """All intelligence scores for a single job."""
    resume_match_pct: float = 0.0
    skill_match_pct: float = 0.0
    experience_match_pct: float = 0.0
    location_match_pct: float = 0.0
    overall_match_pct: float = 0.0
    opportunity_score: float = 0.0
    learning_score: float = 0.0
    salary_score: float = 0.0
    career_growth_score: float = 0.0
    remote_compatibility: float = 0.0
    company_rating: float = 0.0
    difficulty: str = "medium"
    estimated_learning_time: str = ""
    match_explanation: MatchExplanation = Field(default_factory=MatchExplanation)
    # V2: Enhanced scoring
    hiring_probability: float = 0.0  # 0-100, likelihood of getting hired
    confidence_score: float = 0.0    # 0-100, how confident we are in this match


class ScoredJob(BaseModel):
    """A job listing with full intelligence scoring."""
    job: JobListing
    intelligence: JobIntelligence


# ─────────────────── Learning Engine ───────────────────

class LearningResource(BaseModel):
    """A single learning recommendation."""
    skill: str
    resource_name: str
    provider: str
    url: str = ""
    learning_match_pct: float = 0.0
    career_impact_pct: float = 0.0
    resume_improvement_pct: float = 0.0
    estimated_time: str = ""
    difficulty: str = "medium"
    certificate_available: bool = False
    description: str = ""


# ─────────────────── Certification Engine ───────────────────

class CertificationRecommendation(BaseModel):
    """A certification recommendation."""
    name: str
    provider: str
    url: str = ""
    resume_match_increase: float = 0.0
    estimated_salary_impact: str = ""
    industry_demand: str = "high"
    learning_time: str = ""
    difficulty: str = "medium"
    related_skills: List[str] = []
    # V2: Enhanced fields
    free: bool = False
    exam_cost: str = ""
    study_hours: int = 0
    resume_boost_pct: float = 0.0
    salary_impact_pct: float = 0.0
    career_impact_pct: float = 0.0
    popularity: int = 0
    demand: str = "medium"
    official_link: str = ""
    relevance_score: float = 0.0
    skill_match_pct: float = 0.0


# ─────────────────── Resume ROI ───────────────────

class ROIAction(BaseModel):
    """A single ROI action item."""
    action: str
    category: str  # skill, certification, project, resume, experience
    resume_increase_pct: float = 0.0
    career_impact: str = "medium"
    estimated_time: str = ""
    difficulty: str = "medium"
    priority: int = 0  # higher = more impact


# ─────────────────── Career Roadmap ───────────────────

class RoadmapTask(BaseModel):
    """A single task in the career roadmap."""
    task: str
    category: str
    estimated_time: str = ""
    career_score_impact: float = 0.0
    completed: bool = False


class CareerRoadmap(BaseModel):
    """30/60/90 day career roadmap."""
    day_30: List[RoadmapTask] = []
    day_60: List[RoadmapTask] = []
    day_90: List[RoadmapTask] = []
    total_career_score_increase: float = 0.0


# ─────────────────── Career Dashboard ───────────────────

class CareerDashboard(BaseModel):
    """Dynamic career dashboard metrics."""
    career_score: float = 0.0
    career_score_change: float = 0.0
    resume_strength: float = 0.0
    interview_readiness: float = 0.0
    skill_gap_score: float = 0.0
    applications_count: int = 0
    interviews_count: int = 0
    offers_count: int = 0
    today_goal: str = ""
    new_opportunities: int = 0
    learning_progress: float = 0.0
    weekly_improvement: float = 0.0
    ai_daily_insight: str = ""
    top_missing_skills: List[str] = []
    recommended_actions: List[str] = []


# ─────────────────── Job Details Page ───────────────────

class JobDetails(BaseModel):
    """Full job analysis for the details modal."""
    job: JobListing
    intelligence: JobIntelligence
    resume_suggestions: List[str] = []
    interview_difficulty: str = ""
    likely_questions: List[str] = []
    company_research: str = ""
    tech_stack: List[str] = []
    hiring_process: str = ""
    ai_recommendation: str = ""


# ─────────────────── Internship CRUD ───────────────────

class InternshipBase(BaseModel):
    title: str
    company: str
    location: str
    description: str
    stipend: Optional[str] = None
    remote: bool = False
    apply_link: str = ""
    source: str = "manual"

class InternshipCreate(InternshipBase):
    pass

class Internship(InternshipBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    posted_date: datetime = Field(default_factory=datetime.utcnow)

class InternshipUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    stipend: Optional[str] = None
    remote: Optional[bool] = None
    apply_link: Optional[str] = None
    source: Optional[str] = None


# ─────────────────── API Response Models ───────────────────

class RecommendationResponse(BaseModel):
    resume_data: Optional[ResumeData] = None
    jobs: List[ScoredJob] = []
    ai_suggestions: str = ""
    sources_searched: List[str] = []
    search_filters: Optional[SearchFilters] = None
    learning: List[LearningResource] = []
    certifications: List[CertificationRecommendation] = []
    roi_actions: List[ROIAction] = []
    career_roadmap: Optional[CareerRoadmap] = None
    dashboard: Optional[CareerDashboard] = None
    # Discovery metadata
    total_found: int = 0
    by_platform: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    by_recency: Dict[str, int] = {}
    platform_status: Dict[str, str] = {}  # platform -> "ok" | "error" | "timeout"
    # V2: Certification discovery
    certification_discovery: List[Dict] = []
