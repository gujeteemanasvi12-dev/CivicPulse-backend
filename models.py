from pydantic import BaseModel
from typing import Optional


class ComplaintInput(BaseModel):
    description: str
    ward: Optional[str] = None
    image_url: Optional[str] = None


class ComplaintResponse(BaseModel):
    complaint_id: str
    category: str
    department: str
    priority: str
    priority_score: int
    status: str
    officer_message: str
    created_at: str