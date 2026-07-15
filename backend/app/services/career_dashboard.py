"""
Career Dashboard Generator.
Creates dynamic career dashboard with metrics, insights, and daily goals.
"""
from typing import List
from app.models.schemas import (
    ResumeData, CareerDashboard, JobIntelligence,
    LearningResource, ROIAction, CareerRoadmap,
)


def generate_dashboard(
    resume: ResumeData,
    scored_jobs: List[JobIntelligence],
    learning: List[LearningResource],
    roi_actions: List[ROIAction],
    roadmap: CareerRoadmap,
) -> CareerDashboard:
    """Generate dynamic career dashboard."""

    # Calculate career score
    career_score = _calculate_career_score(resume, scored_jobs)

    # Resume strength
    resume_strength = _calculate_resume_strength(resume)

    # Interview readiness
    interview_readiness = _calculate_interview_readiness(resume, scored_jobs)

    # Skill gap
    skill_gap = _calculate_skill_gap(scored_jobs)

    # Top missing skills
    all_missing = []
    for intel in scored_jobs:
        all_missing.extend(intel.match_explanation.missing_skills)
    from collections import Counter
    top_missing = [skill for skill, _ in Counter(all_missing).most_common(5)]

    # Today's goal
    today_goal = _generate_daily_goal(career_score, top_missing, roi_actions)

    # AI daily insight
    ai_insight = _generate_ai_insight(career_score, resume_strength, top_missing, len(scored_jobs))

    # Recommended actions
    recommended = _generate_recommended_actions(career_score, top_missing, roi_actions)

    # Learning progress
    learning_progress = 20.0 if len(resume.skills) > 5 else 10.0  # Placeholder

    # New opportunities
    new_opps = sum(1 for j in scored_jobs if j.overall_match_pct > 60)

    return CareerDashboard(
        career_score=career_score,
        career_score_change=3.0,
        resume_strength=resume_strength,
        interview_readiness=interview_readiness,
        skill_gap_score=skill_gap,
        applications_count=0,
        interviews_count=0,
        offers_count=0,
        today_goal=today_goal,
        new_opportunities=new_opps,
        learning_progress=learning_progress,
        weekly_improvement=2.5,
        ai_daily_insight=ai_insight,
        top_missing_skills=top_missing,
        recommended_actions=recommended,
    )


def _calculate_career_score(resume: ResumeData, scored_jobs: List[JobIntelligence]) -> float:
    """Calculate overall career score (0-100)."""
    base = 30.0

    # Skills contribution
    skill_bonus = min(len(resume.skills) * 2.5, 25.0)

    # Experience contribution
    exp_bonus = min(resume.years_experience * 5, 15.0)

    # Education contribution
    edu_bonus = 5.0 if resume.education else 0.0

    # Job match contribution
    if scored_jobs:
        avg_match = sum(j.overall_match_pct for j in scored_jobs) / len(scored_jobs)
        match_bonus = avg_match * 0.15
    else:
        match_bonus = 0.0

    score = base + skill_bonus + exp_bonus + edu_bonus + match_bonus
    return min(round(score, 1), 100.0)


def _calculate_resume_strength(resume: ResumeData) -> float:
    """Calculate resume strength score."""
    score = 20.0

    # Skills
    score += min(len(resume.skills) * 3, 30.0)

    # Experience
    score += min(len(resume.experience) * 5, 25.0)

    # Education
    score += min(len(resume.education) * 5, 15.0)

    # Projects
    score += min(len(resume.projects) * 5, 10.0)

    return min(round(score, 1), 100.0)


def _calculate_interview_readiness(resume: ResumeData, scored_jobs: List[JobIntelligence]) -> float:
    """Calculate interview readiness score."""
    score = 15.0

    # Technical breadth
    score += min(len(resume.skills) * 2, 30.0)

    # Experience depth
    score += min(len(resume.experience) * 5, 20.0)

    # Job market fit
    if scored_jobs:
        avg_skill = sum(j.skill_match_pct for j in scored_jobs) / len(scored_jobs)
        score += avg_skill * 0.2

    return min(round(score, 1), 100.0)


def _calculate_skill_gap(scored_jobs: List[JobIntelligence]) -> float:
    """Calculate skill gap score (higher = smaller gap)."""
    if not scored_jobs:
        return 50.0

    avg_skill_match = sum(j.skill_match_pct for j in scored_jobs) / len(scored_jobs)
    return round(avg_skill_match, 1)


def _generate_daily_goal(career_score: float, top_missing: List[str], roi_actions: List[ROIAction]) -> str:
    """Generate a personalized daily goal."""
    if career_score < 40:
        return "Focus on building foundational skills - complete 1 online course module today"
    elif career_score < 60:
        if top_missing:
            return f"Spend 2 hours learning {top_missing[0]} - it's your highest-impact gap"
        return "Apply to 5 positions and practice 1 coding problem"
    elif career_score < 80:
        return "Apply to 3 high-quality positions and work on your portfolio project"
    else:
        return "You're in great shape! Apply to 2 dream companies and refine your interview stories"


def _generate_ai_insight(career_score: float, resume_strength: float, top_missing: List[str], job_count: int) -> str:
    """Generate AI daily insight."""
    if career_score < 40:
        return f"Good morning! Your Career Score is {career_score}. Focus on building skills in {', '.join(top_missing[:2]) if top_missing else 'your field'}. Every course you complete will significantly boost your profile."
    elif career_score < 60:
        return f"Good morning! Your Career Score is {career_score} and trending up. With {job_count} matching opportunities found, now is a great time to apply. Address {top_missing[0] if top_missing else 'skill gaps'} to unlock more roles."
    elif career_score < 80:
        return f"Good morning! Your Career Score is {career_score} - strong profile! You have {job_count} well-matched opportunities. Focus on interview prep and tailoring applications for maximum impact."
    else:
        return f"Good morning! Your Career Score is {career_score} - exceptional! You're competitive for top roles. Focus on networking and ace those interviews!"


def _generate_recommended_actions(career_score: float, top_missing: List[str], roi_actions: List[ROIAction]) -> List[str]:
    """Generate recommended actions for today."""
    actions = []

    if top_missing:
        actions.append(f"Learn {top_missing[0]} - highest impact skill gap")

    actions.append("Update resume with quantified achievements")
    actions.append("Apply to 3-5 positions matching your profile")

    if career_score < 50:
        actions.append("Complete 1 online course module")
    else:
        actions.append("Practice 1 coding interview problem")

    actions.append("Connect with 2 professionals on LinkedIn")

    return actions[:5]
