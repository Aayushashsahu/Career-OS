"""
Career Roadmap Generator.
Generates 30/60/90 day career improvement roadmaps.
"""
from typing import List
from app.models.schemas import (
    ResumeData, RoadmapTask, CareerRoadmap,
    LearningResource, CertificationRecommendation, ROIAction,
)


def generate_roadmap(
    resume: ResumeData,
    missing_skills: List[str],
    learning: List[LearningResource],
    certifications: List[CertificationRecommendation],
    roi_actions: List[ROIAction],
) -> CareerRoadmap:
    """Generate a 30/60/90 day career roadmap."""

    day_30 = _generate_30_day_plan(resume, missing_skills, learning)
    day_60 = _generate_60_day_plan(resume, missing_skills, learning, certifications)
    day_90 = _generate_90_day_plan(resume, certifications, roi_actions)

    total_increase = sum(t.career_score_impact for t in day_30 + day_60 + day_90)

    return CareerRoadmap(
        day_30=day_30,
        day_60=day_60,
        day_90=day_90,
        total_career_score_increase=round(total_increase, 1),
    )


def _generate_30_day_plan(resume: ResumeData, missing_skills: List[str], learning: List[LearningResource]) -> List[RoadmapTask]:
    """Generate first 30 days plan - foundation building."""
    tasks = []

    # Week 1: Resume & Profile Optimization
    tasks.append(RoadmapTask(
        task="Optimize resume with quantified achievements",
        category="resume",
        estimated_time="3 hours",
        career_score_impact=3.0,
    ))
    tasks.append(RoadmapTask(
        task="Update LinkedIn profile with new headline and summary",
        category="resume",
        estimated_time="2 hours",
        career_score_impact=2.5,
    ))
    tasks.append(RoadmapTask(
        task="Pin top 3 projects on GitHub profile",
        category="project",
        estimated_time="1 hour",
        career_score_impact=2.0,
    ))

    # Week 2: Start Learning #1 priority skill
    if missing_skills:
        skill = missing_skills[0]
        tasks.append(RoadmapTask(
            task=f"Complete {skill} fundamentals course",
            category="skill",
            estimated_time="10 hours",
            career_score_impact=5.0,
        ))
        tasks.append(RoadmapTask(
            task=f"Build a small {skill} project",
            category="project",
            estimated_time="8 hours",
            career_score_impact=4.0,
        ))

    # Week 3: Continue Learning + Start Applying
    if len(missing_skills) > 1:
        tasks.append(RoadmapTask(
            task=f"Start learning {missing_skills[1]}",
            category="skill",
            estimated_time="5 hours",
            career_score_impact=3.0,
        ))
    tasks.append(RoadmapTask(
        task="Apply to 10 quality positions",
        category="application",
        estimated_time="5 hours",
        career_score_impact=2.0,
    ))

    # Week 4: Practice & Apply
    tasks.append(RoadmapTask(
        task="Practice coding interviews (2 sessions)",
        category="interview",
        estimated_time="6 hours",
        career_score_impact=3.0,
    ))
    tasks.append(RoadmapTask(
        task="Apply to 15 more positions",
        category="application",
        estimated_time="6 hours",
        career_score_impact=2.5,
    ))

    return tasks


def _generate_60_day_plan(resume: ResumeData, missing_skills: List[str], learning: List[LearningResource], certifications: List[CertificationRecommendation]) -> List[RoadmapTask]:
    """Generate days 31-60 plan - skill building & networking."""
    tasks = []

    # Skill Deep Dive
    if missing_skills:
        tasks.append(RoadmapTask(
            task=f"Complete advanced {missing_skills[0]} project",
            category="project",
            estimated_time="15 hours",
            career_score_impact=6.0,
        ))

    if len(missing_skills) > 1:
        tasks.append(RoadmapTask(
            task=f"Finish {missing_skills[1]} certification or course",
            category="skill",
            estimated_time="20 hours",
            career_score_impact=5.0,
        ))

    # Certification
    if certifications:
        cert = certifications[0]
        tasks.append(RoadmapTask(
            task=f"Start preparing for {cert.name}",
            category="certification",
            estimated_time="15 hours",
            career_score_impact=4.0,
        ))

    # Networking
    tasks.append(RoadmapTask(
        task="Connect with 20 professionals in target field",
        category="networking",
        estimated_time="3 hours",
        career_score_impact=2.0,
    ))
    tasks.append(RoadmapTask(
        task="Attend 1 virtual tech meetup or webinar",
        category="networking",
        estimated_time="2 hours",
        career_score_impact=1.5,
    ))

    # Applications
    tasks.append(RoadmapTask(
        task="Apply to 20 positions with tailored resumes",
        category="application",
        estimated_time="10 hours",
        career_score_impact=3.0,
    ))

    # GitHub
    tasks.append(RoadmapTask(
        task="Contribute to 1 open source project",
        category="project",
        estimated_time="8 hours",
        career_score_impact=3.5,
    ))

    return tasks


def _generate_90_day_plan(resume: ResumeData, certifications: List[CertificationRecommendation], roi_actions: List[ROIAction]) -> List[RoadmapTask]:
    """Generate days 61-90 plan - advanced skills & interview prep."""
    tasks = []

    # Advanced Skills
    tasks.append(RoadmapTask(
        task="Build a portfolio-worthy project showcasing all skills",
        category="project",
        estimated_time="20 hours",
        career_score_impact=7.0,
    ))

    # Certification completion
    if certifications:
        tasks.append(RoadmapTask(
            task=f"Complete {certifications[0].name} certification",
            category="certification",
            estimated_time="20 hours",
            career_score_impact=5.0,
        ))

    # Interview Prep
    tasks.append(RoadmapTask(
        task="Complete 10 mock technical interviews",
        category="interview",
        estimated_time="10 hours",
        career_score_impact=5.0,
    ))
    tasks.append(RoadmapTask(
        task="Prepare 5 STAR stories for behavioral questions",
        category="interview",
        estimated_time="5 hours",
        career_score_impact=3.0,
    ))

    # Strategic Applications
    tasks.append(RoadmapTask(
        task="Apply to 25 positions at top-tier companies",
        category="application",
        estimated_time="12 hours",
        career_score_impact=4.0,
    ))

    # Personal Brand
    tasks.append(RoadmapTask(
        task="Write 1 technical blog post or tutorial",
        category="brand",
        estimated_time="6 hours",
        career_score_impact=3.0,
    ))
    tasks.append(RoadmapTask(
        task="Share project on LinkedIn with technical writeup",
        category="brand",
        estimated_time="2 hours",
        career_score_impact=2.0,
    ))

    return tasks
