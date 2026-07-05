# agents.py
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def call_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text.strip()


# ── AGENT 1: Understand the complaint ──────────────────────────
def agent_understand(description: str, ward: str) -> dict:
    prompt = f"""
You are a municipal complaint classifier for Indian cities.
Analyze this citizen complaint and extract structured information.

Complaint: "{description}"
Ward/Area: "{ward}"

Respond ONLY with a valid JSON object and nothing else. No explanation, no markdown.
The JSON must have exactly these keys:
- "category": one of [Roads, Water, Electricity, Sanitation, Streetlights, Noise, Parks, Other]
- "urgency": one of [Low, Medium, High, Critical]
- "location_hint": a short extracted location string from the complaint (or the ward if not mentioned)
- "affected_people_estimate": an integer estimate of how many people are affected
- "summary": a one-sentence plain English summary of the complaint

Example output:
{{"category": "Roads", "urgency": "High", "location_hint": "MG Road near bus stop", "affected_people_estimate": 200, "summary": "Large pothole on MG Road causing accidents and traffic delays."}}
"""
    raw = call_gemini(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find('{')
        end = raw.rfind('}') + 1
        return json.loads(raw[start:end])


# ── AGENT 2: Route to correct department ───────────────────────
DEPARTMENT_MAP = {
    "Roads": "Roads and Infrastructure Department",
    "Water": "Water Supply Department",
    "Electricity": "Electrical Department",
    "Sanitation": "Sanitation and Waste Management Department",
    "Streetlights": "Electrical Department",
    "Noise": "Environment and Noise Pollution Department",
    "Parks": "Parks and Recreation Department",
    "Other": "General Administration Department"
}

OFFICER_EMAILS = {
    "Roads and Infrastructure Department": "roads.officer@panvel.gov.in",
    "Water Supply Department": "water.officer@panvel.gov.in",
    "Electrical Department": "electrical.officer@panvel.gov.in",
    "Sanitation and Waste Management Department": "sanitation.officer@panvel.gov.in",
    "Environment and Noise Pollution Department": "environment.officer@panvel.gov.in",
    "Parks and Recreation Department": "parks.officer@panvel.gov.in",
    "General Administration Department": "admin.officer@panvel.gov.in"
}

def agent_route(category: str) -> dict:
    department = DEPARTMENT_MAP.get(category, "General Administration Department")
    officer_email = OFFICER_EMAILS.get(department, "admin.officer@panvel.gov.in")
    return {
        "department": department,
        "officer_email": officer_email
    }


# ── AGENT 3: Score priority ─────────────────────────────────────
def agent_prioritize(category: str, urgency: str, affected_people: int, repeat_complaint: bool) -> dict:
    prompt = f"""
You are a municipal priority scoring engine.
Score this complaint from 1 to 100 based on urgency and impact.

Details:
- Category: {category}
- Urgency level: {urgency}
- Estimated people affected: {affected_people}
- Is this a repeated complaint from this area: {repeat_complaint}

Rules:
- Critical urgency = base score 70-100
- High urgency = base score 50-70
- Medium urgency = base score 30-50
- Low urgency = base score 1-30
- Add up to 20 points if people affected > 500
- Add 10 points if it is a repeated complaint
- Sanitation and Water complaints get +10 for health risk
- Never exceed 100

Respond ONLY with a valid JSON object:
{{"priority_score": <integer 1-100>, "priority_label": "<Critical|High|Medium|Low>", "reasoning": "<one sentence>"}}
"""
    raw = call_gemini(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find('{')
        end = raw.rfind('}') + 1
        return json.loads(raw[start:end])


# ── AGENT 4: Draft officer communication ───────────────────────
def agent_draft_communication(complaint_id: str, summary: str, department: str,
                               officer_email: str, priority_label: str, location: str) -> str:
    prompt = f"""
Draft a formal official communication from a municipal AI system to a government officer.
This must sound professional and authoritative, like a real government notice.

Details:
- Complaint ID: {complaint_id}
- Summary: {summary}
- Assigned Department: {department}
- Officer Email: {officer_email}
- Priority: {priority_label}
- Location: {location}

Write a formal letter/notice of 3-4 short paragraphs.
Include: reference to the complaint ID, nature of the issue, urgency, requested action timeline,
and a note that the citizen will be notified upon resolution.
Do NOT use markdown formatting. Plain text only.
"""
    return call_gemini(prompt)


# ── AGENT 5: Escalation message drafter ────────────────────────
def agent_escalate(complaint_id: str, summary: str, department: str,
                   hours_elapsed: int, original_officer: str) -> str:
    prompt = f"""
A citizen complaint has not been resolved after {hours_elapsed} hours.
Draft an escalation notice to the senior officer of the department.

Complaint ID: {complaint_id}
Summary: {summary}
Department: {department}
Originally assigned to: {original_officer}
Hours since filing: {hours_elapsed}

Write a firm but professional escalation notice of 2-3 paragraphs.
Mention the failure to act within the deadline, reference the complaint ID, and demand immediate action.
Plain text only. No markdown.
"""
    return call_gemini(prompt)