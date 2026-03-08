from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    return templates.TemplateResponse("home.html", {"request": request, "org": org})


@router.post("/setup")
async def setup_org(
    request: Request,
    name: str = Form(...),
    industry: str = Form(...),
    org_chart_text: str = Form(""),
    tool_stack: str = Form(""),
    bottlenecks: str = Form(""),
    db: Session = Depends(get_db),
):
    tool_list = [t.strip() for t in tool_stack.split(",") if t.strip()]
    bottleneck_list = [b.strip() for b in bottlenecks.splitlines() if b.strip()]

    org = db.query(Organization).first()
    if org:
        org.name = name
        org.industry = industry
        org.org_chart_text = org_chart_text
        org.tool_stack_json = tool_list
        org.bottlenecks_json = bottleneck_list
    else:
        org = Organization(
            name=name,
            industry=industry,
            org_chart_text=org_chart_text,
            tool_stack_json=tool_list,
            bottlenecks_json=bottleneck_list,
        )
        db.add(org)
    db.commit()
    return RedirectResponse(url="/discovery", status_code=303)
