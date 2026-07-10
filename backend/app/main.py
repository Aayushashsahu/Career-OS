from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI(
    title="CareerOS Internship API",
    description="API for managing internships with AI-powered recommendations",
    version="0.1.0",
)

# In-memory storage
internships_db = {}

# Pydantic models
class InternshipBase(BaseModel):
    title: str = Field(..., example="Software Engineering Intern")
    company: str = Field(..., example="Tech Corp")
    location: str = Field(..., example="San Francisco, CA")
    description: str = Field(..., example="Work on exciting projects...")
    stipend: Optional[float] = Field(None, example=3000.0)
    remote: bool = Field(False, example=True)
    apply_link: str = Field(..., example="https://example.com/apply")
    posted_date: datetime = Field(default_factory=datetime.utcnow)

class InternshipCreate(InternshipBase):
    pass

class Internship(InternshipBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4'))

class InternshipUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    stipend: Optional[float] = None
    remote: Optional[bool] = None
    apply_link: Optional[str] = None

# Helper functions
def get_internship(internship_id: str):
    return internships_db.get(internship_id)

# Routes
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to CareerOS Internship API"}

@app.post("/internships", response_model=Internship, status_code=status.HTTP_201_CREATED, tags=["Internships"])
async def create_internship(internship: InternshipCreate):
    internship_obj = Internship(**internship.dict())
    internships_db[internship_obj.id] = internship_obj
    return internship_obj

@app.get("/internships", response_model=List[Internship], tags=["Internships"])
async def list_internships(skip: int = 0, limit: int = 100):
    return list(internships_db.values())[skip:skip+limit]

@app.get("/internships/{internship_id}", response_model=Internship, tags=["Internships"])
async def get_internship(internship_id: str):
    internship = get_internship(internship_id)
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")
    return internship

@app.put("/internships/{internship_id}", response_model=Internship, tags=["Internships"])
async def update_internship(internship_id: str, internship_update: InternshipUpdate):
    stored = get_internship(internship_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Internship not found")
    update_data = internship_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stored, field, value)
    internships_db[internship_id] = stored
    return stored

@app.delete("/internships/{internship_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Internships"])
async def delete_internship(internship_id: str):
    if not get_internship(internship_id):
        raise HTTPException(status_code=404, detail="Internship not found")
    del internships_db[internship_id]
    return None

# Placeholder recommendation endpoint (to be enhanced with Gemini/NVIDIA NIM)
@app.get("/recommendations/{user_id}", tags=["Recommendations"])
async def get_recommendations(user_id: str):
    """
    Return internship recommendations for a user.
    In a real implementation, this would call Gemini/NVIDIA NIM with user profile.
    For now, returns a few sample internships.
    """
    # If we have internships, return some; otherwise return empty list
    if not internships_db:
        return []
    # Simple logic: return first 3 internships as recommendations
    return list(internships_db.values())[:3]

# Note: To integrate Gemini, you would:
# 1. Install google-generativeai
# 2. Configure API key via environment variable
# 3. Create a function that takes user profile and returns suggested internships
# 4. Call that function in the recommendation endpoint.