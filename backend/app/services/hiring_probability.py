"""
Hiring Probability & Confidence Score Engine.
Calculates the likelihood of getting hired and confidence in the match.
"""
from typing import List, Optional, Tuple
from app.models.schemas import JobListing, ResumeData, JobIntelligence

# Known top-tier companies (for hiring probability adjustments)
FAANG_COMPANIES = [
    "google", "microsoft", "amazon", "apple", "meta", "netflix",
    "nvidia", "tesla", "salesforce", "adobe", "oracle", "ibm",
    "uber", "airbnb", "spotify", "databricks", "snowflake",
    "stripe", "cloudflare", "vercel", "notion", "anthropic",
    "openai", "deepmind", "bytedance", "shopify", "block",
]

STARTUP_SIGNALS = [
    "series a", "series b", "series c", "seed", "pre-seed",
    "startup", "early stage", "yc", "y combinator", "techstars",
    "accelerator", "funded",
]


def calculate_hiring_probability(
    job: JobListing,
    intelligence: JobIntelligence,
    resume: ResumeData,
) -> float:
    """
    Calculate probability of getting hired (0-100).
    Based on: skill match, experience fit, company competitiveness, job freshness.
    """
    score = 50.0  # Base probability

    # 1. Skill match impact (most important)
    skill = intelligence.skill_match_pct
    if skill >= 80:
        score += 20
    elif skill >= 60:
        score += 12
    elif skill >= 40:
        score += 5
    else:
        score -= 10

    # 2. Experience level fit
    exp = intelligence.experience_match_pct
    if exp >= 80:
        score += 10
    elif exp >= 50:
        score += 5
    else:
        score -= 5

    # 3. Company competitiveness (harder companies = lower probability)
    company_lower = job.company.lower()
    is_faang = any(c in company_lower for c in FAANG_COMPANIES)
    if is_faang:
        score -= 15  # FAANG is more competitive
    # Startups are easier to get into
    is_startup = any(s in company_lower or s in job.description.lower() for s in STARTUP_SIGNALS)
    if is_startup:
        score += 10

    # 4. Job freshness (newer = better chance)
    if job.freshness_score >= 90:
        score += 8  # Just posted
    elif job.freshness_score >= 70:
        score += 4
    elif job.freshness_score < 30:
        score -= 5  # Old listing, many applicants

    # 5. Employment type
    if job.employment_type == "internship":
        score += 5  # Internships generally easier
    elif job.employment_type == "contract":
        score += 8  # Contract roles often easier

    # 6. Remote roles have more competition
    if job.remote:
        score -= 3

    # 7. Easy apply = higher chance (less friction)
    if job.apply_link and "easy" in job.apply_link.lower():
        score += 5

    return max(5.0, min(95.0, round(score, 1)))


def calculate_confidence_score(
    job: JobListing,
    intelligence: JobIntelligence,
    resume: ResumeData,
) -> float:
    """
    Calculate confidence in the match quality (0-100).
    Based on: data completeness, skill data quality, description richness.
    """
    score = 50.0
    factors = 0
    total = 0

    # 1. Has skills_required data
    if job.skills_required:
        score += 15
    factors += 1
    total += 1

    # 2. Has description
    if job.description and len(job.description) > 100:
        score += 10
    factors += 1
    total += 1

    # 3. Has salary info
    if job.salary or job.stipend:
        score += 5
    factors += 1
    total += 1

    # 4. Has experience_required
    if job.experience_required:
        score += 5
    factors += 1
    total += 1

    # 5. Has posted_date
    if job.posted_date:
        score += 5
    factors += 1
    total += 1

    # 6. Multiple sources (dedup confidence)
    if len(job.sources) > 1:
        score += 10
    factors += 1
    total += 1

    # 7. Skills match has data
    if intelligence.match_explanation.matched_skills:
        score += 5
    factors += 1
    total += 1

    # Penalize if very few skills detected
    if len(resume.skills) < 3:
        score -= 10

    return max(10.0, min(95.0, round(score, 1)))


def enhance_intelligence(
    job: JobListing,
    intelligence: JobIntelligence,
    resume: ResumeData,
) -> JobIntelligence:
    """Add hiring_probability and confidence_score to existing intelligence."""
    hiring_prob = calculate_hiring_probability(job, intelligence, resume)
    confidence = calculate_confidence_score(job, intelligence, resume)

    intelligence.hiring_probability = hiring_prob
    intelligence.confidence_score = confidence

    return intelligence
