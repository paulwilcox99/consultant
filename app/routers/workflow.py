from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, Process, WorkflowMap
from app.services.claude_client import stream_claude
from app.services.context_builder import get_org_context, get_process_context
from app.services.parsers import extract_workflow_data
from app.prompts.workflow import WORKFLOW_SYSTEM_PROMPT

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def workflow_page(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        return RedirectResponse(url="/", status_code=303)
    processes = db.query(Process).order_by(Process.department, Process.rank).all()
    departments = sorted(set(p.department for p in processes if p.department))
    workflow_maps = db.query(WorkflowMap).order_by(WorkflowMap.created_at.desc()).all()
    return templates.TemplateResponse(
        "steps/workflow.html",
        {
            "request": request,
            "org": org,
            "processes": processes,
            "departments": departments,
            "workflow_maps": workflow_maps,
        },
    )


@router.post("/map")
async def workflow_map(
    department: str = Form(...),
    plain_english: str = Form(...),
    process_id: str = Form(""),
    db: Session = Depends(get_db),
):
    org_ctx = get_org_context(db)
    process_ctx = get_process_context(db)

    user_msg = (
        f"Organization Context:\n{org_ctx}\n\n"
        f"Process Inventory:\n{process_ctx}\n\n"
        f"Department: {department}\n\n"
        f"Process Description:\n{plain_english}"
    )

    messages = [{"role": "user", "content": user_msg}]

    async def generate():
        full_response = []
        async for chunk in stream_claude(WORKFLOW_SYSTEM_PROMPT, messages, max_tokens=4096):
            full_response.append(chunk)
            yield f"data: {chunk.replace(chr(10), '\\n')}\n\n"
        yield "data: [DONE]\n\n"

        response_text = "".join(full_response)
        parsed = extract_workflow_data(response_text)

        pid = int(process_id) if process_id.isdigit() else None
        db_session = next(get_db())
        try:
            wm = WorkflowMap(
                department=department,
                plain_english_input=plain_english,
                mermaid_diagram=parsed["mermaid"],
                flagged_handoffs_json=parsed["handoffs"],
                flagged_redundancies_json=parsed["redundancies"],
                automation_triggers_json=parsed["triggers"],
                process_id=pid,
            )
            db_session.add(wm)
            db_session.commit()
        finally:
            db_session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/maps", response_class=HTMLResponse)
async def workflow_maps_list(request: Request, db: Session = Depends(get_db)):
    workflow_maps = db.query(WorkflowMap).order_by(WorkflowMap.created_at.desc()).all()
    return templates.TemplateResponse(
        "partials/workflow_maps_list.html",
        {"request": request, "workflow_maps": workflow_maps},
    )


@router.delete("/maps/{map_id}")
async def delete_workflow_map(map_id: int, db: Session = Depends(get_db)):
    wm = db.query(WorkflowMap).filter(WorkflowMap.id == map_id).first()
    if wm:
        db.delete(wm)
        db.commit()
    return HTMLResponse("")
