# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import ComplaintInput
from agents import (agent_understand, agent_route, agent_prioritize,
                    agent_draft_communication, agent_escalate)
from database import (save_complaint, get_complaint, get_all_complaints,
                      check_repeat_complaint, run_query)
from scheduler import start_scheduler
import uuid

app = FastAPI(title="CivicPulse Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    start_scheduler()

@app.get("/")
def root():
    return {"message": "CivicPulse backend is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/debug")
def debug():
    result = run_query("MATCH (c:Complaint) RETURN c LIMIT 1")
    return result

@app.post("/complaint/submit")
def submit_complaint(complaint: ComplaintInput):
    try:
        ward = complaint.ward or "Unknown"
        understanding = agent_understand(complaint.description, ward)
        routing = agent_route(understanding["category"])
        is_repeat = check_repeat_complaint(ward, understanding["category"])
        priority_info = agent_prioritize(
            category=understanding["category"],
            urgency=understanding["urgency"],
            affected_people=understanding["affected_people_estimate"],
            repeat_complaint=is_repeat
        )
        temp_id = str(uuid.uuid4())[:8].upper()
        officer_message = agent_draft_communication(
            complaint_id=temp_id,
            summary=understanding["summary"],
            department=routing["department"],
            officer_email=routing["officer_email"],
            priority_label=priority_info["priority_label"],
            location=understanding["location_hint"]
        )
        data_to_save = {
            "description": complaint.description,
            "category": understanding["category"],
            "department": routing["department"],
            "ward": ward,
            "priority": priority_info["priority_label"],
            "priority_score": priority_info["priority_score"],
            "officer_email": routing["officer_email"],
            "officer_message": officer_message,
            "summary": understanding["summary"],
            "location_hint": understanding["location_hint"]
        }
        complaint_id = save_complaint(data_to_save)
        return {
            "complaint_id": complaint_id,
            "category": understanding["category"],
            "department": routing["department"],
            "priority": priority_info["priority_label"],
            "priority_score": priority_info["priority_score"],
            "urgency": understanding["urgency"],
            "summary": understanding["summary"],
            "location_hint": understanding["location_hint"],
            "officer_email": routing["officer_email"],
            "officer_message": officer_message,
            "status": "Filed",
            "message": "Your complaint has been filed and routed to the correct department."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")

@app.get("/complaint/{complaint_id}")
def get_single_complaint(complaint_id: str):
    complaint = get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@app.get("/complaints/all")
def get_all():
    return get_all_complaints()