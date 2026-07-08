# database.py
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import uuid

load_dotenv()

NEO4J_URL = "https://10b3e9c8.databases.neo4j.io/db/10b3e9c8/query/v2"
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def run_query(cypher: str, params: dict = {}):
    response = requests.post(
        NEO4J_URL,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        headers={"Content-Type": "application/json"},
        json={"statement": cypher, "parameters": params}
    )
    return response.json()

def extract_nodes(result):
    try:
        # Format 1: {"data": {"values": [[node], [node]]}}
        values = result.get("data", {}).get("values", [])
        if values:
            nodes = []
            for row in values:
                item = row[0]
                if isinstance(item, dict) and "properties" in item:
                    nodes.append(item["properties"])
                elif isinstance(item, dict):
                    nodes.append(item)
            return nodes
        # Format 2: {"results": [{"data": [{"row": [node]}]}]}
        results = result.get("results", [])
        if results:
            nodes = []
            for row in results[0].get("data", []):
                item = row.get("row", [{}])[0]
                if isinstance(item, dict):
                    nodes.append(item)
            return nodes
    except:
        pass
    return []

def save_complaint(data: dict) -> str:
    complaint_id = str(uuid.uuid4())[:8].upper()
    run_query("""
        CREATE (c:Complaint {
            id: $id, description: $description, category: $category,
            department: $department, ward: $ward, priority: $priority,
            priority_score: $priority_score, status: $status,
            officer_email: $officer_email, officer_message: $officer_message,
            summary: $summary, location_hint: $location_hint,
            created_at: $created_at, escalated: false
        })
    """, {
        "id": complaint_id,
        "description": data["description"],
        "category": data["category"],
        "department": data["department"],
        "ward": data.get("ward", "Unknown"),
        "priority": data["priority"],
        "priority_score": data["priority_score"],
        "status": "Filed",
        "officer_email": data["officer_email"],
        "officer_message": data["officer_message"],
        "summary": data["summary"],
        "location_hint": data["location_hint"],
        "created_at": datetime.utcnow().isoformat()
    })
    return complaint_id

def get_complaint(complaint_id: str):
    result = run_query(
        "MATCH (c:Complaint {id: $id}) RETURN c",
        {"id": complaint_id}
    )
    nodes = extract_nodes(result)
    return nodes[0] if nodes else None

def get_all_complaints() -> list:
    result = run_query(
        "MATCH (c:Complaint) RETURN c ORDER BY c.priority_score DESC"
    )
    return extract_nodes(result)

def get_pending_complaints() -> list:
    result = run_query("""
        MATCH (c:Complaint)
        WHERE c.status <> 'Resolved' AND c.escalated = false
        RETURN c
    """)
    return extract_nodes(result)

def mark_escalated(complaint_id: str):
    run_query("""
        MATCH (c:Complaint {id: $id})
        SET c.escalated = true, c.status = 'Escalated'
    """, {"id": complaint_id})

def check_repeat_complaint(ward: str, category: str) -> bool:
    result = run_query("""
        MATCH (c:Complaint {ward: $ward, category: $category})
        RETURN count(c) as count
    """, {"ward": ward, "category": category})
    try:
        values = result.get("data", {}).get("values", [])
        if values:
            return values[0][0] > 0
    except:
        pass
    return False