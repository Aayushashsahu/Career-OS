"""
Learning Engine.
Recommends courses, certifications, and learning resources based on missing skills.
"""
from typing import List, Dict
from app.models.schemas import LearningResource, CertificationRecommendation, ROIAction


# Course database - maps skills to learning resources
COURSE_DB: Dict[str, List[Dict]] = {
    "python": [
        {"name": "Python for Everybody", "provider": "Coursera", "url": "https://www.coursera.org/specializations/python", "time": "8 weeks", "difficulty": "easy", "cert": True},
        {"name": "Python Course", "provider": "freeCodeCamp", "url": "https://www.freecodecamp.org/learn/", "time": "4 weeks", "difficulty": "easy", "cert": False},
        {"name": "Kaggle Python", "provider": "Kaggle Learn", "url": "https://www.kaggle.com/learn/python", "time": "5 hours", "difficulty": "easy", "cert": True},
    ],
    "javascript": [
        {"name": "JavaScript Algorithms and Data Structures", "provider": "freeCodeCamp", "url": "https://www.freecodecamp.org/learn", "time": "6 weeks", "difficulty": "medium", "cert": True},
        {"name": "The Complete JavaScript Course", "provider": "Udemy", "url": "https://www.udemy.com/course/the-complete-javascript-course/", "time": "10 weeks", "difficulty": "medium", "cert": True},
    ],
    "react": [
        {"name": "React - The Complete Guide", "provider": "Udemy", "url": "https://www.udemy.com/course/react-the-complete-guide-incl-redux/", "time": "8 weeks", "difficulty": "medium", "cert": True},
        {"name": "Meta Front-End Developer", "provider": "Coursera", "url": "https://www.coursera.org/professional-certificates/meta-frontend-developer", "time": "7 months", "difficulty": "medium", "cert": True},
    ],
    "docker": [
        {"name": "Docker for Beginners", "provider": "Linux Foundation", "url": "https://training.linuxfoundation.org/", "time": "2 weeks", "difficulty": "easy", "cert": False},
        {"name": "Docker Course", "provider": "freeCodeCamp", "url": "https://www.youtube.com/watch?v=fqMOX6JJhGo", "time": "3 hours", "difficulty": "easy", "cert": False},
        {"name": "Docker Official Training", "provider": "Docker", "url": "https://www.docker.com/trainings/", "time": "4 weeks", "difficulty": "medium", "cert": True},
    ],
    "kubernetes": [
        {"name": "Kubernetes for Beginners", "provider": "KodeKloud", "url": "https://kodekloud.com/", "time": "4 weeks", "difficulty": "medium", "cert": False},
        {"name": "CKAD Prep Course", "provider": "Linux Foundation", "url": "https://training.linuxfoundation.org/", "time": "8 weeks", "difficulty": "hard", "cert": True},
    ],
    "aws": [
        {"name": "AWS Cloud Practitioner", "provider": "AWS Skill Builder", "url": "https://skillbuilder.aws/", "time": "20 hours", "difficulty": "easy", "cert": True},
        {"name": "AWS Solutions Architect", "provider": "Coursera", "url": "https://www.coursera.org/professional-certificates/aws-cloud-solutions-architect", "time": "3 months", "difficulty": "medium", "cert": True},
    ],
    "azure": [
        {"name": "Azure Fundamentals (AZ-900)", "provider": "Microsoft Learn", "url": "https://learn.microsoft.com/", "time": "15 hours", "difficulty": "easy", "cert": True},
        {"name": "Azure AI Engineer", "provider": "Microsoft Learn", "url": "https://learn.microsoft.com/", "time": "40 hours", "difficulty": "medium", "cert": True},
    ],
    "machine learning": [
        {"name": "Machine Learning Specialization", "provider": "Coursera (DeepLearning.AI)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "time": "3 months", "difficulty": "medium", "cert": True},
        {"name": "ML with Python", "provider": "freeCodeCamp", "url": "https://www.freecodecamp.org/learn", "time": "4 weeks", "difficulty": "medium", "cert": True},
        {"name": "Intro to ML", "provider": "Google Cloud Skills Boost", "url": "https://cloud.google.com/training/machinelearning-ai", "time": "2 weeks", "difficulty": "easy", "cert": False},
    ],
    "deep learning": [
        {"name": "Deep Learning Specialization", "provider": "Coursera (DeepLearning.AI)", "url": "https://www.coursera.org/specializations/deep-learning", "time": "4 months", "difficulty": "hard", "cert": True},
        {"name": "Fast.ai Practical Deep Learning", "provider": "fast.ai", "url": "https://course.fast.ai/", "time": "7 weeks", "difficulty": "medium", "cert": False},
    ],
    "tensorflow": [
        {"name": "TensorFlow Developer Certificate", "provider": "DeepLearning.AI", "url": "https://www.coursera.org/professional-certificates/tensorflow-in-practice", "time": "4 months", "difficulty": "medium", "cert": True},
        {"name": "TensorFlow 2.0 Course", "provider": "Udemy", "url": "https://www.udemy.com/course/tensorflow-20-deep-learning-and-artificial-intelligence/", "time": "6 weeks", "difficulty": "medium", "cert": True},
    ],
    "pytorch": [
        {"name": "PyTorch for Deep Learning", "provider": "Udemy", "url": "https://www.udemy.com/course/pytorch-for-deep-learning/", "time": "6 weeks", "difficulty": "medium", "cert": True},
        {"name": "PyTorch Course", "provider": "freeCodeCamp", "url": "https://www.youtube.com/watch?v=GI1-6z8XS3o", "time": "12 hours", "difficulty": "medium", "cert": False},
    ],
    "sql": [
        {"name": "SQL for Data Science", "provider": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science", "time": "4 weeks", "difficulty": "easy", "cert": True},
        {"name": "SQL Course", "provider": "Kaggle Learn", "url": "https://www.kaggle.com/learn/intro-to-sql", "time": "3 hours", "difficulty": "easy", "cert": True},
    ],
    "git": [
        {"name": "Git & GitHub Course", "provider": "freeCodeCamp", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "time": "4 hours", "difficulty": "easy", "cert": False},
        {"name": "Git Learning", "provider": "GitHub Skills", "url": "https://skills.github.com/", "time": "2 weeks", "difficulty": "easy", "cert": False},
    ],
    "node.js": [
        {"name": "Node.js, Express, MongoDB Bootcamp", "provider": "Udemy", "url": "https://www.udemy.com/course/nodejs-express-mongodb-bootcamp/", "time": "8 weeks", "difficulty": "medium", "cert": True},
    ],
    "terraform": [
        {"name": "HashiCorp Terraform Associate", "provider": "HashiCorp Learn", "url": "https://developer.hashicorp.com/terraform/tutorials", "time": "4 weeks", "difficulty": "medium", "cert": True},
    ],
    "figma": [
        {"name": "Figma UI Design Course", "provider": "Udemy", "url": "https://www.udemy.com/course/figma-ux-ui-design/", "time": "4 weeks", "difficulty": "easy", "cert": True},
    ],
}

# Certification database
CERT_DB: Dict[str, List[Dict]] = {
    "aws": [
        {"name": "AWS Cloud Practitioner", "provider": "Amazon", "url": "https://aws.amazon.com/certification/", "salary_impact": "+15% entry level", "demand": "very high", "time": "20 hours", "difficulty": "easy"},
        {"name": "AWS Solutions Architect Associate", "provider": "Amazon", "url": "https://aws.amazon.com/certification/", "salary_impact": "+25% mid level", "demand": "very high", "time": "80 hours", "difficulty": "medium"},
    ],
    "azure": [
        {"name": "Azure Fundamentals (AZ-900)", "provider": "Microsoft", "url": "https://learn.microsoft.com/en-us/certifications/", "salary_impact": "+12% entry level", "demand": "high", "time": "15 hours", "difficulty": "easy"},
        {"name": "Azure AI Engineer (AI-102)", "provider": "Microsoft", "url": "https://learn.microsoft.com/en-us/certifications/", "salary_impact": "+30% AI roles", "demand": "high", "time": "60 hours", "difficulty": "medium"},
    ],
    "google_cloud": [
        {"name": "Google Cloud Digital Leader", "provider": "Google", "url": "https://cloud.google.com/certification", "salary_impact": "+10% entry level", "demand": "high", "time": "20 hours", "difficulty": "easy"},
        {"name": "Google Professional ML Engineer", "provider": "Google", "url": "https://cloud.google.com/certification", "salary_impact": "+35% ML roles", "demand": "very high", "time": "100 hours", "difficulty": "hard"},
    ],
    "kubernetes": [
        {"name": "CKAD (Certified Kubernetes Application Developer)", "provider": "Linux Foundation", "url": "https://training.linuxfoundation.org/", "salary_impact": "+25% DevOps", "demand": "very high", "time": "80 hours", "difficulty": "hard"},
        {"name": "CKA (Certified Kubernetes Administrator)", "provider": "Linux Foundation", "url": "https://training.linuxfoundation.org/", "salary_impact": "+30% DevOps", "demand": "very high", "time": "100 hours", "difficulty": "hard"},
    ],
    "tensorflow": [
        {"name": "TensorFlow Developer Certificate", "provider": "Google", "url": "https://www.tensorflow.org/certificate", "salary_impact": "+20% ML roles", "demand": "high", "time": "80 hours", "difficulty": "medium"},
    ],
    "meta": [
        {"name": "Meta Front-End Developer Certificate", "provider": "Meta (Coursera)", "url": "https://www.coursera.org/professional-certificates/meta-frontend-developer", "salary_impact": "+15% frontend", "demand": "high", "time": "7 months", "difficulty": "medium"},
        {"name": "Meta Back-End Developer Certificate", "provider": "Meta (Coursera)", "url": "https://www.coursera.org/professional-certificates/meta-back-end-developer", "salary_impact": "+15% backend", "demand": "high", "time": "7 months", "difficulty": "medium"},
    ],
    "data_science": [
        {"name": "IBM Data Science Professional", "provider": "IBM (Coursera)", "url": "https://www.coursera.org/professional-certificates/ibm-data-science", "salary_impact": "+20% data roles", "demand": "high", "time": "5 months", "difficulty": "medium"},
    ],
}


def recommend_courses(missing_skills: List[str], matched_skills: List[str]) -> List[LearningResource]:
    """Recommend courses based on missing skills."""
    recommendations = []

    for skill in missing_skills:
        skill_lower = skill.lower()
        courses = []

        # Find courses in DB
        for db_skill, course_list in COURSE_DB.items():
            if db_skill in skill_lower or skill_lower in db_skill:
                courses = course_list
                break

        if not courses:
            # Generic recommendation
            courses = [
                {"name": f"{skill} Course", "provider": "freeCodeCamp", "url": f"https://www.freecodecamp.org/", "time": "4 weeks", "difficulty": "medium", "cert": False},
            ]

        for course in courses[:2]:  # Max 2 per skill
            # Calculate match percentages
            learning_match = 85.0 if len(matched_skills) > 3 else 70.0
            career_impact = 80.0 if skill_lower in ["python", "javascript", "react", "docker", "aws", "machine learning"] else 65.0
            resume_improvement = 6.0 if len(missing_skills) <= 3 else 4.0

            recommendations.append(LearningResource(
                skill=skill,
                resource_name=course["name"],
                provider=course["provider"],
                url=course["url"],
                learning_match_pct=learning_match,
                career_impact_pct=career_impact,
                resume_improvement_pct=resume_improvement,
                estimated_time=course.get("time", "4 weeks"),
                difficulty=course.get("difficulty", "medium"),
                certificate_available=course.get("cert", False),
                description=f"Learn {skill} to improve your resume match by ~{resume_improvement:.0f}%",
            ))

    return recommendations


def recommend_certifications(missing_skills: List[str], matched_skills: List[str]) -> List[CertificationRecommendation]:
    """Recommend certifications based on skills profile."""
    recommendations = []
    seen = set()

    for skill in missing_skills + matched_skills:
        skill_lower = skill.lower()

        for db_skill, cert_list in CERT_DB.items():
            if db_skill in skill_lower or skill_lower in db_skill:
                for cert in cert_list:
                    if cert["name"] not in seen:
                        seen.add(cert["name"])
                        resume_increase = 8.0 if skill_lower in missing_skills else 4.0

                        recommendations.append(CertificationRecommendation(
                            name=cert["name"],
                            provider=cert["provider"],
                            url=cert["url"],
                            resume_match_increase=resume_increase,
                            estimated_salary_impact=cert["salary_impact"],
                            industry_demand=cert["demand"],
                            learning_time=cert["time"],
                            difficulty=cert["difficulty"],
                            related_skills=[skill],
                        ))

    return recommendations[:8]


def calculate_roi_actions(
    missing_skills: List[str],
    matched_skills: List[str],
    certifications: List[CertificationRecommendation],
) -> List[ROIAction]:
    """Calculate Resume ROI - what actions give the highest career return."""
    actions = []

    # Skill-based actions
    for i, skill in enumerate(missing_skills[:5]):
        priority = len(missing_skills) - i
        actions.append(ROIAction(
            action=f"Learn {skill}",
            category="skill",
            resume_increase_pct=5.0 + (priority * 0.5),
            career_impact="high" if skill.lower() in ["python", "javascript", "react", "docker", "aws"] else "medium",
            estimated_time="2-4 weeks",
            difficulty="medium",
            priority=priority,
        ))

    # Certification actions
    for i, cert in enumerate(certifications[:3]):
        actions.append(ROIAction(
            action=f"Get {cert.name}",
            category="certification",
            resume_increase_pct=cert.resume_match_increase,
            career_impact="high" if cert.industry_demand == "very high" else "medium",
            estimated_time=cert.learning_time,
            difficulty=cert.difficulty,
            priority=10 - i,
        ))

    # Project-based actions
    if matched_skills:
        top_skill = matched_skills[0] if matched_skills else "Python"
        actions.append(ROIAction(
            action=f"Build a {top_skill} project for GitHub",
            category="project",
            resume_increase_pct=7.0,
            career_impact="high",
            estimated_time="1-2 weeks",
            difficulty="medium",
            priority=8,
        ))

    # Resume improvement actions
    actions.append(ROIAction(
        action="Quantify internship achievements with numbers",
        category="resume",
        resume_increase_pct=3.0,
        career_impact="medium",
        estimated_time="2 hours",
        difficulty="easy",
        priority=6,
    ))

    actions.append(ROIAction(
        action="Improve GitHub profile with pinned repos",
        category="resume",
        resume_increase_pct=3.0,
        career_impact="medium",
        estimated_time="1 hour",
        difficulty="easy",
        priority=5,
    ))

    # Sort by priority (higher = more impact)
    actions.sort(key=lambda a: a.priority, reverse=True)

    return actions
