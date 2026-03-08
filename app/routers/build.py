from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, AutomationOpportunity, WorkflowBuild
from app.services.claude_client import stream_claude
from app.services.context_builder import build_build_context
from app.services.parsers import extract_build_data
from app.prompts.build import BUILD_SYSTEM_PROMPT

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def build_page(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return RedirectResponse(url="/", status_code=303)
    opportunities = db.query(AutomationOpportunity).order_by(AutomationOpportunity.rank).all()
    builds = db.query(WorkflowBuild).all()
    built_opportunity_ids = set(b.opportunity_id for b in builds)
    return templates.TemplateResponse(
        "steps/build.html",
        {
            "request": request,
            "org": org,
            "opportunities": opportunities,
            "builds": builds,
            "built_opportunity_ids": built_opportunity_ids,
        },
    )


@router.post("/generate")
async def build_generate(
    opportunity_id: int = Form(...),
    db: Session = Depends(get_db),
):
    context = build_build_context(db, opportunity_id)
    messages = [
        {"role": "user", "content": f"Generate workflow configurations for all 4 platforms:\n\n{context}"}
    ]

    async def generate():
        full_response = []
        async for chunk in stream_claude(BUILD_SYSTEM_PROMPT, messages, max_tokens=8096):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        parsed = extract_build_data(response_text)

        db_session = next(get_db())
        try:
            # Remove existing builds for this opportunity
            db_session.query(WorkflowBuild).filter(
                WorkflowBuild.opportunity_id == opportunity_id
            ).delete()

            for platform, code in parsed.items():
                if code:
                    db_session.add(WorkflowBuild(
                        opportunity_id=opportunity_id,
                        platform=platform,
                        workflow_json=code,
                        documentation="",
                    ))

            # Update opportunity status
            opp = db_session.query(AutomationOpportunity).filter(
                AutomationOpportunity.id == opportunity_id
            ).first()
            if opp:
                opp.status = "completed"

            db_session.commit()
        finally:
            db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{opportunity_id}/results", response_class=HTMLResponse)
async def build_results(request: Request, opportunity_id: int, db: Session = Depends(get_db)):
    opp = db.query(AutomationOpportunity).filter(AutomationOpportunity.id == opportunity_id).first()
    builds = (
        db.query(WorkflowBuild)
        .filter(WorkflowBuild.opportunity_id == opportunity_id)
        .all()
    )
    builds_by_platform = {b.platform: b for b in builds}
    return templates.TemplateResponse(
        "partials/build_results.html",
        {
            "request": request,
            "opportunity": opp,
            "builds": builds_by_platform,
        },
    )
