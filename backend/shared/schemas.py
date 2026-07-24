# backend/shared/schemas.py
from pydantic import BaseModel
from typing import Literal, Optional

CategoryCode = Literal["DSA","COD","OOD","APTI","COMM","AI","CLOUD","SQL","SWE","SYSD","NETW","OS","OTHER"]

class Skill(BaseModel):
    skill_name: str
    category_code: CategoryCode
    evidence: str
    confidence: Literal["high", "medium", "low"]

class ExtractedSkillList(BaseModel):
    source_type: Literal["jd", "resume"]
    source_file: str
    company: Optional[str] = None
    role: Optional[str] = None
    skills: list[Skill]

class CandidateProfile(BaseModel):
    name: str
    email: str
    education: Optional[str] = None
    skills: list[Skill] = []
    hackathons: list[str] = []
    internships: list[str] = []
    certifications: list[str] = []
    preferred_roles: list[str] = []
    cv_file: Optional[str] = None

class SkillGap(BaseModel):
    category_code: CategoryCode
    required_level: int   # 1-10
    candidate_level: int  # 1-10
    gap: bool

class TalentCheckResult(BaseModel):
    company: str
    skillset_gap: list[SkillGap]
    readiness_score: int  # 0-100

class SkillMatchResult(BaseModel):
    jd_source_file: str
    match_score: int  # 0-100
    matched_skills: list[str]
    missing_skills: list[str]