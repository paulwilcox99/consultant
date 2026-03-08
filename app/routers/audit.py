from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, WorkflowMap, AutomationOpportunity, ImplementationPhase
from app.services.claude_client import stream_claude
from app.services.context_builder import build_audit_context
from app.services.parsers import extract_json_block, parse_opportunities
from app.prompts.audit import AUDIT_SYSTEM_PROMPT

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def audit_page(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return RedirectResponse(url="/", status_code=303)
    workflow_maps = db.query(WorkflowMap).order_by(WorkflowMap.created_at).all()
    opportunities = (
        db.query(AutomationOpportunity)
        .order_by(AutomationOpportunity.rank)
        .all()
    )
    return templates.TemplateResponse(
        "steps/audit.html",
        {
            "request": request,
            "org": org,
            "workflow_maps": workflow_maps,
            "opportunities": opportunities,
        },
    )


@router.post("/run")
async def audit_run(db: Session = Depends(get_db)):
    context = build_audit_context(db)
    messages = [
        {"role": "user", "content": f"Please analyze this organization and identify the top 10 automation opportunities:\n\n{context}"}
    ]

    async def generate():
        full_response = []
        async for chunk in stream_claude(AUDIT_SYSTEM_PROMPT, messages, max_tokens=6000):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        json_data = extract_json_block(response_text)
        if json_data:
            opportunities = parse_opportunities(json_data)
            db_session = next(get_db())
            try:
                # Clear existing
                db_session.query(AutomationOpportunity).delete()
                for opp in opportunities:
                    db_session.add(AutomationOpportunity(**opp))
                db_session.commit()

                # Auto-generate implementation phases
                _generate_phases(db_session, opportunities)
                db_session.commit()
            finally:
                db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


def _generate_phases(db, opportunities):
    """Auto-generate 3 implementation phases from opportunities."""
    db.query(ImplementationPhase).delete()

    low = [o for o in opportunities if o.get("complexity") == "low"]
    medium = [o for o in opportunities if o.get("complexity") == "medium"]
    high = [o for o in opportunities if o.get("complexity") == "high"]

    phases = [
        {
            "name": "Phase 1: Quick Wins",
            "description": "Low complexity automations for immediate ROI",
            "phase_order": 1,
            "tasks_json": [
                {"title": o["title"], "completed": False, "roi": o["roi_score"]}
                for o in low
            ],
        },
        {
            "name": "Phase 2: Medium Complexity",
            "description": "Medium complexity automations with significant impact",
            "phase_order": 2,
            "tasks_json": [
                {"title": o["title"], "completed": False, "roi": o["roi_score"]}
                for o in medium
            ],
        },
        {
            "name": "Phase 3: Complex Builds",
            "description": "High complexity automation projects",
            "phase_order": 3,
            "tasks_json": [
                {"title": o["title"], "completed": False, "roi": o["roi_score"]}
                for o in high
            ],
        },
    ]

    for phase_data in phases:
        db.add(ImplementationPhase(**phase_data))
