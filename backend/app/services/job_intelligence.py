"""
Job Intelligence Scoring Engine.
Calculates match percentages, opportunity scores, and provides explanations.
"""
import re
from typing import List, Optional, Tuple
from app.models.schemas import (
    JobListing, ResumeData, SearchFilters,
    JobIntelligence, MatchExplanation, ScoredJob,
)


def score_job(job: JobListing, resume: ResumeData, filters: Optional[SearchFilters] = None) -> ScoredJob:
    """Score a single job against the user's resume and filters."""
    intelligence = _calculate_intelligence(job, resume, filters)
    # V2: Add hiring probability and confidence score
    try:
        from app.services.hiring_probability import enhance_intelligence
        intelligence = enhance_intelligence(job, intelligence, resume)
    except Exception:
        pass
    return ScoredJob(job=job, intelligence=intelligence)


def score_jobs(jobs: List[JobListing], resume: ResumeData, filters: Optional[SearchFilters] = None) -> List[ScoredJob]:
    """Score all jobs and sort by overall match."""
    scored = [score_job(job, resume, filters) for job in jobs]
    scored.sort(key=lambda s: s.intelligence.overall_match_pct, reverse=True)
    return scored


def _calculate_intelligence(job: JobListing, resume: ResumeData, filters: Optional[SearchFilters] = None) -> JobIntelligence:
    """Calculate all intelligence scores for a job."""

    # Skill matching
    skill_match, matched, missing = _calculate_skill_match(job, resume)

    # Experience matching
    exp_match = _calculate_experience_match(job, resume)

    # Location matching
    loc_match = _calculate_location_match(job, filters)

    # Opportunity score (how good is this opportunity)
    opp_score = _calculate_opportunity_score(job, skill_match, resume)

    # Learning score (how much will you learn)
    learn_score = _calculate_learning_score(job, missing, skill_match)

    # Salary score
    salary_score = _calculate_salary_score(job)

    # Career growth score
    growth_score = _calculate_growth_score(job, skill_match)

    # Remote compatibility
    remote_compat = _calculate_remote_compatibility(job, filters)

    # Company rating (placeholder - could be enhanced with real data)
    company_rating = 3.5  # Default

    # Overall match (weighted average)
    overall = (
        skill_match * 0.35 +
        exp_match * 0.15 +
        loc_match * 0.15 +
        opp_score * 0.15 +
        learn_score * 0.10 +
        salary_score * 0.05 +
        growth_score * 0.05
    )

    # Difficulty
    difficulty = "easy" if skill_match > 70 else "medium" if skill_match > 40 else "hard"

    # Estimated learning time
    if len(missing) == 0:
        learn_time = "Ready to apply"
    elif len(missing) <= 2:
        learn_time = "1-2 weeks"
    elif len(missing) <= 4:
        learn_time = "1-2 months"
    else:
        learn_time = "3+ months"

    # Build explanation
    explanation = _build_explanation(job, resume, matched, missing, skill_match, exp_match, loc_match)

    return JobIntelligence(
        resume_match_pct=round(overall, 1),
        skill_match_pct=round(skill_match, 1),
        experience_match_pct=round(exp_match, 1),
        location_match_pct=round(loc_match, 1),
        overall_match_pct=round(overall, 1),
        opportunity_score=round(opp_score, 1),
        learning_score=round(learn_score, 1),
        salary_score=round(salary_score, 1),
        career_growth_score=round(growth_score, 1),
        remote_compatibility=round(remote_compat, 1),
        company_rating=company_rating,
        difficulty=difficulty,
        estimated_learning_time=learn_time,
        match_explanation=explanation,
    )


def _calculate_skill_match(job: JobListing, resume: ResumeData) -> Tuple[float, List[str], List[str]]:
    """Calculate skill match percentage using word-boundary matching."""
    import re

    # Skills from job (required)
    job_skills = set(s.lower() for s in job.skills_required)
    if not job_skills:
        # Infer from title and description
        job_skills = set(s.lower() for s in job.skills_found)

    # User skills
    user_skills = [s.lower() for s in resume.skills]

    if not job_skills:
        return 50.0, [], []  # No data, neutral score

    def _skills_overlap(skill_a: str, skill_b: str) -> bool:
        """Check if two skills match using word-boundary regex to avoid false positives."""
        # Direct equality
        if skill_a == skill_b:
            return True
        # Check if one is contained in the other as a whole word
        try:
            if re.search(r'\b' + re.escape(skill_a) + r'\b', skill_b):
                return True
            if re.search(r'\b' + re.escape(skill_b) + r'\b', skill_a):
                return True
        except re.error:
            # Fallback to substring if regex fails
            return skill_a in skill_b or skill_b in skill_a
        return False

    matched = []
    missing = []
    for s in job_skills:
        if any(_skills_overlap(s, us) for us in user_skills):
            matched.append(s)
        else:
            missing.append(s)

    match_pct = (len(matched) / len(job_skills)) * 100 if job_skills else 50.0

    return min(match_pct, 100.0), matched, missing


def _calculate_experience_match(job: JobListing, resume: ResumeData) -> float:
    """Calculate experience level match."""
    if not job.experience_required:
        return 60.0  # Neutral if not specified

    exp_text = job.experience_required.lower()

    # Parse required experience
    if any(w in exp_text for w in ["0", "entry", "junior", "fresh", "intern", "student"]):
        required_level = 0
    elif any(w in exp_text for w in ["1-2", "1-3", "1 to 3"]):
        required_level = 1
    elif any(w in exp_text for w in ["3-5", "3 to 5", "mid"]):
        required_level = 3
    elif any(w in exp_text for w in ["5+", "5 to", "senior", "lead"]):
        required_level = 5
    else:
        required_level = 1

    user_exp = resume.years_experience

    if user_exp >= required_level:
        return min(100.0, 80.0 + (user_exp - required_level) * 5)
    else:
        gap = required_level - user_exp
        return max(20.0, 80.0 - gap * 20)


def _calculate_location_match(job: JobListing, filters: Optional[SearchFilters] = None) -> float:
    """Calculate location match."""
    if not filters:
        return 70.0

    job_loc = job.location.lower()

    # Remote match
    if filters.work_style == "remote" or (filters.work_style == "any" and job.remote):
        return 90.0 if job.remote else 60.0

    if filters.work_style == "on-site" and job.remote:
        return 30.0

    # City match
    if filters.city and filters.city.lower() in job_loc:
        return 95.0

    # Country match
    if filters.country and filters.country.lower() in job_loc:
        return 80.0

    if job.remote:
        return 75.0

    return 50.0


def _calculate_opportunity_score(job: JobListing, skill_match: float, resume: ResumeData) -> float:
    """Calculate how good this opportunity is."""
    score = 50.0

    # Higher score for better skill match
    score += skill_match * 0.3

    # Bonus for well-known companies
    big_tech = ["google", "microsoft", "amazon", "apple", "meta", "netflix", "stripe", "airbnb"]
    if any(c in job.company.lower() for c in big_tech):
        score += 15

    # Bonus for startups (learning opportunity)
    startup_signals = ["startup", "seed", "series a", "series b", "yc", "y combinator"]
    if any(s in job.company.lower() or s in job.description.lower() for s in startup_signals):
        score += 10

    # Bonus for remote
    if job.remote:
        score += 5

    return min(score, 100.0)


def _calculate_learning_score(job: JobListing, missing_skills: List[str], skill_match: float) -> float:
    """Calculate learning potential."""
    if skill_match > 80:
        return 40.0  # Already knows most, less learning
    elif skill_match > 50:
        return 75.0  # Good balance of known and new
    else:
        return 60.0  # Too many gaps, might be overwhelming


def _calculate_salary_score(job: JobListing) -> float:
    """Calculate salary competitiveness score."""
    if not job.salary and not job.stipend:
        return 50.0

    salary_text = (job.salary or job.stipend or "").lower()

    # Parse salary
    import re
    numbers = re.findall(r'\d+', salary_text.replace(",", ""))
    if not numbers:
        return 50.0

    max_num = max(int(n) for n in numbers)

    # Normalize to monthly INR scale
    if "lakh" in salary_text or "lpa" in salary_text:
        monthly = max_num * 100000 / 12
    elif "year" in salary_text or "annum" in salary_text or "annual" in salary_text:
        monthly = max_num / 12
    elif "k" in salary_text:
        monthly = max_num * 1000
    else:
        monthly = max_num

    if monthly >= 100000:
        return 95.0
    elif monthly >= 50000:
        return 80.0
    elif monthly >= 25000:
        return 65.0
    elif monthly >= 10000:
        return 50.0
    else:
        return 35.0


def _calculate_growth_score(job: JobListing, skill_match: float) -> float:
    """Calculate career growth potential."""
    score = 50.0

    # Tech roles have higher growth
    tech_keywords = ["engineer", "developer", "scientist", "architect", "lead"]
    if any(k in job.title.lower() for k in tech_keywords):
        score += 15

    # AI/ML roles have highest growth
    ai_keywords = ["ai", "ml", "machine learning", "deep learning", "data science"]
    if any(k in job.title.lower() for k in ai_keywords):
        score += 15

    # Good skill match means you can grow
    if skill_match > 50:
        score += 10

    return min(score, 100.0)


def _calculate_remote_compatibility(job: JobListing, filters: Optional[SearchFilters] = None) -> float:
    """Calculate how compatible the job is with remote work."""
    if job.remote:
        return 95.0

    if filters and filters.work_style == "remote":
        return 20.0

    return 50.0


def _build_explanation(
    job: JobListing,
    resume: ResumeData,
    matched: List[str],
    missing: List[str],
    skill_match: float,
    exp_match: float,
    loc_match: float,
) -> MatchExplanation:
    """Build detailed match explanation."""
    reasons_for = []
    reasons_against = []

    # Skill reasons
    if matched:
        reasons_for.append(f"✓ Skills match: {', '.join(matched[:5])}")
    if missing:
        reasons_against.append(f"✗ Missing: {', '.join(missing[:5])}")

    # Experience reasons
    if exp_match >= 70:
        reasons_for.append("✓ Experience level matches")
    elif exp_match < 40:
        reasons_against.append("✗ Experience level mismatch")

    # Location reasons
    if loc_match >= 70:
        reasons_for.append("✓ Location preference matches")
    elif loc_match < 40:
        reasons_against.append("✗ Location doesn't match preference")

    # Company reasons
    big_tech = ["google", "microsoft", "amazon", "apple", "meta"]
    if any(c in job.company.lower() for c in big_tech):
        reasons_for.append("✓ Top-tier company")

    if job.remote:
        reasons_for.append("✓ Remote-friendly")

    # Experience match text
    if exp_match >= 80:
        exp_text = "Your experience level is a strong fit"
    elif exp_match >= 50:
        exp_text = "Your experience level is a reasonable fit"
    else:
        exp_text = "This role may require more experience"

    # Location match text
    if loc_match >= 80:
        loc_text = "Matches your location preference"
    elif loc_match >= 50:
        loc_text = "Location is acceptable"
    else:
        loc_text = "Different from preferred location"

    return MatchExplanation(
        matched_skills=matched,
        missing_skills=missing,
        experience_match=exp_text,
        location_match=loc_text,
        reasons_for=reasons_for,
        reasons_against=reasons_against,
    )
