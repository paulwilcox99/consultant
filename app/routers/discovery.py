import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, ConversationMessage, Process
from app.services.claude_client import stream_claude, complete_claude
from app.services.context_builder import get_org_context, get_conversation_context
from app.services.parsers import extract_json_block
from app.prompts.discovery import (
    DISCOVERY_SYSTEM_PROMPT,
    DISCOVERY_FINALIZE_PROMPT,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

STEP = "discovery"


@router.get("", response_class=HTMLResponse)
async def discovery_page(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return RedirectResponse(url="/", status_code=303)
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.step == STEP)
        .order_by(ConversationMessage.created_at)
        .all()
    )
    processes = db.query(Process).order_by(Process.rank).all()
    return templates.TemplateResponse(
        "steps/discovery.html",
        {"request": request, "org": org, "messages": messages, "processes": processes},
    )


@router.post("/start")
async def discovery_start(db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return {"error": "No organization set up"}

    org_context = get_org_context(db)
    messages = [
        {
            "role": "user",
            "content": f"Here is our organization data:\n\n{org_context}\n\nPlease ask your clarifying questions.",
        }
    ]

    # Save user message
    db.add(ConversationMessage(step=STEP, role="user", content=messages[0]["content"]))
    db.commit()

    async def generate():
        full_response = []
        async for chunk in stream_claude(DISCOVERY_SYSTEM_PROMPT, messages):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        db_session = next(get_db())
        try:
            db_session.add(ConversationMessage(step=STEP, role="assistant", content=response_text))
            db_session.commit()
        finally:
            db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/reply")
async def discovery_reply(
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    # Build conversation history
    history = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.step == STEP)
        .order_by(ConversationMessage.created_at)
        .all()
    )
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": message})

    # Save user message
    db.add(ConversationMessage(step=STEP, role="user", content=message))
    db.commit()

    async def generate():
        full_response = []
        async for chunk in stream_claude(DISCOVERY_SYSTEM_PROMPT, messages):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        db_session = next(get_db())
        try:
            db_session.add(ConversationMessage(step=STEP, role="assistant", content=response_text))
            db_session.commit()
        finally:
            db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/finalize")
async def discovery_finalize(db: Session = Depends(get_db)):
    conversation = get_conversation_context(db, STEP)
    messages = [
        {"role": "user", "content": f"Full conversation:\n\n{conversation}\n\n{DISCOVERY_FINALIZE_PROMPT}"}
    ]

    response_text = await complete_claude(DISCOVERY_SYSTEM_PROMPT, messages, max_tokens=4096)

    # Parse and save processes
    data = extract_json_block(response_text)
    if data and "processes" in data:
        # Clear existing processes
        db.query(Process).delete()
        for p in data["processes"]:
            db.add(Process(
                name=p.get("name", "Unknown"),
                department=p.get("department", ""),
                description=p.get("description", ""),
                time_cost_hours_per_week=float(p.get("time_cost_hours_per_week", 0)),
                rank=int(p.get("rank", 0)),
            ))
        db.commit()

    return RedirectResponse(url="/discovery", status_code=303)


@router.post("/clear")
async def discovery_clear(db: Session = Depends(get_db)):
    """Clear conversation to start over."""
    db.query(ConversationMessage).filter(ConversationMessage.step == STEP).delete()
    db.commit()
    return RedirectResponse(url="/discovery", status_code=303)
