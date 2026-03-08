from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, AutomationOpportunity, SystemArchitecture
from app.services.claude_client import stream_claude
from app.services.context_builder import build_architecture_context
from app.services.parsers import extract_architecture_data
from app.prompts.architecture import ARCHITECTURE_SYSTEM_PROMPT

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def architecture_page(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return RedirectResponse(url="/", status_code=303)
    opportunities = db.query(AutomationOpportunity).order_by(AutomationOpportunity.rank).all()
    architecture = db.query(SystemArchitecture).first()
    return templates.TemplateResponse(
        "steps/architecture.html",
        {
            "request": request,
            "org": org,
            "opportunities": opportunities,
            "architecture": architecture,
        },
    )


@router.post("/design")
async def architecture_design(db: Session = Depends(get_db)):
    context = build_architecture_context(db)
    messages = [
        {"role": "user", "content": f"Design the automation system architecture for this organization:\n\n{context}"}
    ]

    async def generate():
        full_response = []
        async for chunk in stream_claude(ARCHITECTURE_SYSTEM_PROMPT, messages, max_tokens=6000):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        parsed = extract_architecture_data(response_text)

        db_session = next(get_db())
        try:
            db_session.query(SystemArchitecture).delete()
            arch = SystemArchitecture(
                description=parsed.get("description", ""),
                mermaid_diagram=parsed.get("mermaid", ""),
                agents_json=parsed.get("agents", []),
                linear_flows_json=parsed.get("linear_flows", []),
            )
            db_session.add(arch)
            db_session.commit()
        finally:
            db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")
