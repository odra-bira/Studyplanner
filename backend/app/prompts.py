"""Prompts and tool schemas for Claude, kept apart from the API calls so they're easy to review."""

from __future__ import annotations

from datetime import date

from .dates import weekday

SYSTEM = """You are StudyEase, a study planning assistant for college students.
You are practical and encouraging without being cheesy. You give specific, concrete steps.
You never claim that a plan improves mental health; stress check-ins only change how work is spread out."""

# ---------- tools (forced tool use = structured JSON output) ----------

PLAN_TOOL = {
    "name": "submit_plan",
    "description": "Submit the study sessions for one assignment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sessions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                        "minutes": {"type": "integer", "description": "Multiple of 5, 15 to 180"},
                        "task": {"type": "string", "description": "One concrete step, under 50 characters"},
                        "why": {"type": "string", "description": "One plain sentence on the timing or size, under 110 characters"},
                    },
                    "required": ["date", "minutes", "task", "why"],
                },
            },
            "note": {"type": "string", "description": "One sentence summarizing the plan or what does not fit"},
        },
        "required": ["sessions", "note"],
    },
}

REBALANCE_TOOL = {
    "name": "submit_moves",
    "description": "Submit the sessions to move. Only include sessions that change.",
    "input_schema": {
        "type": "object",
        "properties": {
            "moves": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                        "minutes": {"type": "integer"},
                        "why": {"type": "string", "description": "Short reason, under 100 characters"},
                    },
                    "required": ["id", "date"],
                },
            },
            "note": {"type": "string", "description": "One sentence on what changed and anything that still does not fit"},
        },
        "required": ["moves", "note"],
    },
}

BREAKDOWN_TOOL = {
    "name": "submit_steps",
    "description": "Submit a short checklist for one study session.",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {"type": "array", "items": {"type": "string"}, "description": "3 to 5 steps, each under 60 characters, starting with a verb"},
        },
        "required": ["steps"],
    },
}

ASSESS_TOOL = {
    "name": "report_assessment",
    "description": "Report how difficult an uploaded assignment is and how long it will take.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string", "description": "Your chat reply to the student: 2-4 friendly sentences explaining the rating."},
            "title": {"type": "string", "description": "Short name for the assignment, under 60 characters"},
            "course": {"type": "string", "description": "Course code if visible, else empty string"},
            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            "estimated_hours": {"type": "number", "description": "Realistic total hours for a typical student, 0.5 to 40"},
            "due_date": {"type": ["string", "null"], "description": "YYYY-MM-DD if a due date is stated, else null"},
            "reasons": {"type": "array", "items": {"type": "string"}, "description": "2-4 short reasons behind the difficulty rating"},
            "first_steps": {"type": "array", "items": {"type": "string"}, "description": "2-3 concrete first steps"},
        },
        "required": ["reply", "title", "course", "difficulty", "estimated_hours", "due_date", "reasons", "first_steps"],
    },
}

# ---------- prompt builders ----------


def plan_prompt(a, ctx) -> str:
    busy = "; ".join(
        f"{d.isoformat()} ({weekday(d)}): {m} min" for d, m in sorted(ctx.booked.items()) if ctx.today <= d <= a.due
    ) or "nothing booked yet"
    minutes = round(a.hours * 60)
    course = f" for {a.course}" if a.course else ""
    stress = " Prefer sessions of 45 minutes or less and keep busy days light." if ctx.mood == "high" else ""
    return f"""Split this assignment into study sessions.

Today: {ctx.today.isoformat()} ({weekday(ctx.today)}).
Assignment: "{a.title}"{course}.
Due: {a.due.isoformat()} ({weekday(a.due)}). Difficulty: {a.difficulty}. Student's estimate: {a.hours} hours ({minutes} minutes).
Available study time: {ctx.daily} minutes per day.
Already booked for other assignments: {busy}.
Stress check-in: {ctx.mood or "not given"}.{stress}

Rules:
- Dates from {ctx.today.isoformat()} to {a.due.isoformat()} inclusive.
- Total close to {minutes} minutes (within 10%).
- Stay within the daily limit after existing bookings where possible; say so in the note if it can't fit.
- Each session is one concrete step specific to this kind of work (for a report: outline and sources, first draft, revise, review and submit).
- Harder work starts earlier. The final review lands on or just before the due date."""


def rebalance_prompt(sessions, assignments, ctx) -> str:
    by_id = {a.id: a for a in assignments}
    lines = []
    for s in sessions:
        if s.done:
            continue
        a = by_id.get(s.assignment_id)
        title, due = (a.title, a.due.isoformat()) if a else ("?", "?")
        lines.append(f"{s.id} | {title} (due {due}) | {s.date.isoformat()} | {s.minutes} min | {s.task}")
    listing = "\n".join(lines)
    return f"""Rebalance this student's unfinished study sessions.

Today: {ctx.today.isoformat()} ({weekday(ctx.today)}). Daily limit: {ctx.daily} minutes. Stress check-in: {ctx.mood or "not given"}.
Sessions (id | assignment (due) | date | minutes | step):
{listing}

Rules:
- No day over the daily limit where possible.
- Never before {ctx.today.isoformat()} or after the assignment's due date. Sessions dated before today must move.
- Keep each assignment's steps in their current order.
- Change minutes only if a day can't fit otherwise; never below 15."""


def breakdown_prompt(session, assignment) -> str:
    title = assignment.title if assignment else "unknown"
    course = f" in {assignment.course}" if assignment and assignment.course else ""
    difficulty = assignment.difficulty if assignment else "unknown"
    return f"""Break this study session into 3 to 5 small checklist steps a student can tick off.
Session: "{session.task}" ({session.minutes} minutes)
Assignment: "{title}"{course}, difficulty {difficulty}."""


def assess_prompt(user_text: str, today: date) -> str:
    note = f'\nThe student also wrote: "{user_text}"' if user_text else ""
    return f"""The student uploaded a file: an assignment sheet, or study material such as lecture notes, slides, a reading or a past paper. Today is {today.isoformat()}.
Read it and judge how difficult it is for a typical college student and how many total hours it will realistically take to complete the assignment, or to study and learn the material.
Consider length requirements, research or citations needed, technical depth, number of parts, and unfamiliar skills.{note}"""


def chat_system(plan_summary: str, today: date) -> str:
    return f"""{SYSTEM}

Today is {today.isoformat()} ({weekday(today)}). Here is the student's current plan:
{plan_summary or "No assignments yet."}

Answer questions about their workload and how to study. Keep replies short (under 120 words) unless they ask for detail.
If they want a difficulty rating for an assignment, ask them to upload it with the paperclip button."""
