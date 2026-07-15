"""
Smart Query Generator.
Infers target roles from resume and generates optimized search queries.
NEVER searches using raw skills like "Python Docker Git".
Always infers target roles first, then generates role variations.
"""
from typing import List, Optional, Tuple
from app.models.schemas import ResumeData, SearchFilters


# Skill-to-role mapping
SKILL_ROLE_MAP = {
    # AI/ML
    "python": ["AI Engineer", "Machine Learning Engineer", "Data Scientist", "Backend Engineer"],
    "tensorflow": ["ML Engineer", "Deep Learning Engineer", "AI Researcher"],
    "pytorch": ["ML Engineer", "Deep Learning Engineer", "AI Researcher"],
    "machine learning": ["ML Engineer", "Data Scientist", "AI Engineer"],
    "deep learning": ["Deep Learning Engineer", "AI Researcher", "Computer Vision Engineer"],
    "nlp": ["NLP Engineer", "Conversational AI Engineer", "ML Engineer"],
    "data science": ["Data Scientist", "Data Analyst", "ML Engineer"],
    "llm": ["AI Engineer", "LLM Engineer", "Applied Scientist"],
    "rag": ["AI Engineer", "ML Engineer", "Backend Engineer"],
    "transformers": ["ML Engineer", "AI Engineer", "Research Engineer"],
    "scikit-learn": ["ML Engineer", "Data Scientist", "AI Engineer"],
    "keras": ["ML Engineer", "Deep Learning Engineer", "AI Engineer"],
    "huggingface": ["ML Engineer", "NLP Engineer", "AI Engineer"],
    # Web Development
    "javascript": ["Frontend Engineer", "Full Stack Developer", "Web Developer"],
    "typescript": ["Frontend Engineer", "Full Stack Developer", "Software Engineer"],
    "react": ["React Developer", "Frontend Engineer", "UI Engineer"],
    "angular": ["Angular Developer", "Frontend Engineer", "Web Developer"],
    "vue": ["Vue Developer", "Frontend Engineer", "Web Developer"],
    "next.js": ["Full Stack Developer", "React Developer", "Frontend Engineer"],
    "node.js": ["Backend Engineer", "Full Stack Developer", "Node.js Developer"],
    "express": ["Backend Engineer", "Full Stack Developer", "API Developer"],
    "svelte": ["Frontend Engineer", "Web Developer", "Full Stack Developer"],
    # Backend
    "django": ["Python Developer", "Backend Engineer", "Django Developer"],
    "flask": ["Python Developer", "Backend Engineer", "API Developer"],
    "fastapi": ["Backend Engineer", "Python Developer", "API Developer"],
    "spring": ["Java Developer", "Backend Engineer", "Spring Developer"],
    "laravel": ["PHP Developer", "Backend Engineer", "Laravel Developer"],
    "ruby": ["Ruby Developer", "Backend Engineer", "Rails Developer"],
    "go": ["Go Developer", "Backend Engineer", "Systems Engineer"],
    "rust": ["Rust Developer", "Systems Engineer", "Backend Engineer"],
    "java": ["Java Developer", "Backend Engineer", "Software Engineer"],
    "c++": ["Software Engineer", "Systems Engineer", "Backend Engineer"],
    # Database
    "sql": ["Data Engineer", "Backend Engineer", "Database Developer"],
    "mongodb": ["Backend Engineer", "NoSQL Developer", "Full Stack Developer"],
    "postgresql": ["Backend Engineer", "Database Developer", "Data Engineer"],
    "mysql": ["Backend Engineer", "Database Developer", "Data Engineer"],
    # Cloud/DevOps
    "aws": ["Cloud Engineer", "DevOps Engineer", "AWS Developer"],
    "azure": ["Cloud Engineer", "DevOps Engineer", "Azure Developer"],
    "gcp": ["Cloud Engineer", "DevOps Engineer", "GCP Developer"],
    "docker": ["DevOps Engineer", "Platform Engineer", "Cloud Engineer"],
    "kubernetes": ["DevOps Engineer", "Platform Engineer", "SRE"],
    "terraform": ["DevOps Engineer", "Infrastructure Engineer", "Cloud Engineer"],
    # Mobile
    "react native": ["React Native Developer", "Mobile Developer", "Cross-platform Developer"],
    "flutter": ["Flutter Developer", "Mobile Developer", "Cross-platform Developer"],
    "swift": ["iOS Developer", "Mobile Developer", "Swift Developer"],
    "kotlin": ["Android Developer", "Mobile Developer", "Kotlin Developer"],
    # Blockchain
    "solidity": ["Blockchain Developer", "Web3 Engineer", "Smart Contract Developer"],
    "blockchain": ["Blockchain Developer", "Web3 Engineer", "DApp Developer"],
    # Design
    "figma": ["UI/UX Designer", "Product Designer", "Frontend Developer"],
    "photoshop": ["Graphic Designer", "UI Designer", "Visual Designer"],
    # DevOps
    "jenkins": ["DevOps Engineer", "CI/CD Engineer", "Release Engineer"],
    "ci/cd": ["DevOps Engineer", "Release Engineer", "Platform Engineer"],
    "ansible": ["DevOps Engineer", "Infrastructure Engineer", "Automation Engineer"],
    "linux": ["System Administrator", "DevOps Engineer", "SRE"],
    # Data
    "spark": ["Data Engineer", "Big Data Engineer", "ML Engineer"],
    "hadoop": ["Data Engineer", "Big Data Engineer"],
    "airflow": ["Data Engineer", "ML Engineer", "Backend Engineer"],
    "dbt": ["Data Engineer", "Analytics Engineer"],
    "snowflake": ["Data Engineer", "Analytics Engineer"],
    "tableau": ["Data Analyst", "BI Engineer", "Data Scientist"],
    "power bi": ["Data Analyst", "BI Engineer", "Data Scientist"],
    # Security
    "penetration testing": ["Security Engineer", "Penetration Tester", "Cybersecurity Analyst"],
    "cybersecurity": ["Security Engineer", "Cybersecurity Analyst", "SOC Analyst"],
}

# Seniority level variations to search for each role
SENIORITY_VARIATIONS = {
    "internship": [
        "{role} Intern",
        "{role} Internship",
        "{role} Trainee",
    ],
    "entry": [
        "{role}",
        "Junior {role}",
        "Associate {role}",
        "{role} I",
        "New Grad {role}",
        "Entry Level {role}",
        "Graduate {role}",
    ],
    "mid": [
        "{role}",
        "Mid-Level {role}",
        "Senior {role}",
    ],
    "senior": [
        "Senior {role}",
        "Staff {role}",
        "Lead {role}",
        "{role} Architect",
    ],
}


def infer_target_roles(resume) -> List[str]:
    """
    Infer target roles from resume skills.
    Accepts either a ResumeData object or a List[str] of skills.
    Returns a ranked list of best-fit roles.
    """
    role_scores = {}

    # Accept both ResumeData and List[str]
    if isinstance(resume, list):
        skills_list = resume
    elif hasattr(resume, 'skills'):
        skills_list = resume.skills
    else:
        skills_list = []

    for skill in skills_list:
        skill_lower = skill.lower().strip()
        for known_skill, roles in SKILL_ROLE_MAP.items():
            if known_skill in skill_lower or skill_lower in known_skill:
                for role in roles:
                    role_scores[role] = role_scores.get(role, 0) + 1

    # Sort by frequency
    sorted_roles = sorted(role_scores.items(), key=lambda x: -x[1])

    if not sorted_roles:
        return ["Software Engineer Intern", "Developer Intern", "Technical Intern"]

    return [role for role, score in sorted_roles[:8]]


def get_seniority_level(filters: Optional[SearchFilters] = None) -> str:
    """Map job_type/experience_level to seniority category."""
    if not filters:
        return "entry"

    jt = filters.job_type.lower()
    if "intern" in jt:
        return "internship"

    exp = filters.experience_level
    if exp in ("0-1",):
        return "entry"
    elif exp in ("1-3",):
        return "entry" if jt == "both" else "mid"
    elif exp in ("3-5",):
        return "mid"
    elif exp in ("5+",):
        return "senior"
    return "entry"


def generate_search_queries(
    resume,
    filters: Optional[SearchFilters] = None,
) -> List[Tuple[str, str]]:
    """
    Generate multiple search queries from resume.
    Accepts either a ResumeData object or a List[str] of skills.
    Returns list of (query, location) tuples.
    Each query is a complete search string for a job board.
    """
    # Accept both ResumeData and List[str]
    if isinstance(resume, list):
        skills_list = resume
        resume_skills = resume[:5] if resume else []
    elif hasattr(resume, 'skills'):
        skills_list = resume.skills
        resume_skills = resume.skills[:5]
    else:
        skills_list = []
        resume_skills = []

    roles = infer_target_roles(skills_list)
    seniority = get_seniority_level(filters)
    queries = []

    location = ""
    job_type_suffix = ""

    if filters:
        location = filters.city or filters.country or "India"
        jt = filters.job_type.lower()
        if jt == "internship":
            job_type_suffix = " intern"
        elif jt == "full-time":
            job_type_suffix = " full-time"

        if filters.work_style and filters.work_style != "any":
            job_type_suffix += f" {filters.work_style}"

    # Generate role + seniority variations for top roles
    variations = SENIORITY_VARIATIONS.get(seniority, SENIORITY_VARIATIONS["entry"])

    for role in roles[:4]:
        for template in variations[:3]:  # Top 3 variations per role
            query_str = template.format(role=role)
            queries.append((query_str.strip(), location))

    # Add skill-based role queries (NOT raw skill search)
    for skill in resume_skills[:3]:
        skill_lower = skill.lower()
        # Look up what roles this skill maps to
        mapped_roles = SKILL_ROLE_MAP.get(skill_lower, [])
        if mapped_roles:
            queries.append((f"{mapped_roles[0]}{job_type_suffix}", location))
            break  # Only add one skill-based role query

    # Add combined query (top role + top skill)
    if roles and resume_skills:
        combined = f"{roles[0]} {resume_skills[0]}{job_type_suffix}"
        queries.append((combined.strip(), location))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q, loc in queries:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append((q, loc))

    return unique[:12]  # Max 12 queries


def get_search_variants(query: str, location: str) -> List[Tuple[str, str]]:
    """
    Generate multiple search variants for a single query.
    Used to search across different platforms with optimized queries.
    """
    variants = [(query, location)]

    # If query doesn't include location, add location-specific variant
    if location and location.lower() not in query.lower():
        variants.append((f"{query} {location}", location))

    return variants
