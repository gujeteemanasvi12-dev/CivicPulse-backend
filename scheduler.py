# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_pending_complaints, mark_escalated
from agents import agent_escalate
from datetime import datetime

scheduler = BackgroundScheduler()

def check_and_escalate():
    print(f"[Scheduler] Running escalation check at {datetime.utcnow()}")
    pending = get_pending_complaints()

    for complaint in pending:
        created_at = datetime.fromisoformat(complaint["created_at"])
        hours_elapsed = (datetime.utcnow() - created_at).total_seconds() / 3600

        if hours_elapsed >= 48:
            print(f"[Scheduler] Escalating complaint {complaint['id']}")
            escalation_message = agent_escalate(
                complaint_id=complaint["id"],
                summary=complaint["summary"],
                department=complaint["department"],
                hours_elapsed=int(hours_elapsed),
                original_officer=complaint["officer_email"]
            )
            mark_escalated(complaint["id"])
            print(f"[Escalation Notice]\n{escalation_message}")

def start_scheduler():
    scheduler.add_job(check_and_escalate, 'interval', hours=2, id='escalation_check')
    scheduler.start()
    print("[Scheduler] Escalation scheduler started — checks every 2 hours")