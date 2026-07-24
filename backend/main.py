from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RADIX Talent Match")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount each role's router here as they become ready ---
from role1_jd.router import router as jd_router
# from role2_resume.router import router as resume_router
# from role3_profile.router import router as profile_router
# from role4_talent_check.router import router as talent_check_router
# from role5_skill_match.router import router as skill_match_router

app.include_router(jd_router, prefix="/api/jd", tags=["JD Analytics"])
# app.include_router(resume_router, prefix="/api/resume", tags=["Resume Parsing"])
# app.include_router(profile_router, prefix="/api/profile", tags=["Profile Builder"])
# app.include_router(talent_check_router, prefix="/api/talent-check", tags=["Talent Check"])
# app.include_router(skill_match_router, prefix="/api/skill-match", tags=["Skill Matching"])

@app.get("/health")
def health():
    return {"status": "ok"}