from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Organization, Process, WorkflowMap, AutomationOpportunity,
    SystemArchitecture, WorkflowBuild, KPI, ImplementationPhase,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _get_dashboard_context(db: Session) -> dict:
    org = db.query(Organization).first()
    processes = db.query(Process).order_by(Process.rank).all()
    opportunities = db.query(AutomationOpportunity).order_by(AutomationOpportunity.rank).all()
    workflow_maps = db.query(WorkflowMap).order_by(WorkflowMap.created_at).all()
    architecture = db.query(SystemArchitecture).first()
    builds = db.query(WorkflowBuild).all()
    kpis = db.query(KPI).all()
    phases = db.query(ImplementationPhase).order_by(ImplementationPhase.phase_order).all()

    total_hours = sum(o.annual_hours_saved for o in opportunities)
    completed_builds = len(set(b.opportunity_id for b in builds))
    kpi_with_target = [k for k in kpis if k.target > 0]
    kpi_pct = (
        len([k for k in kpi_with_target if k.value >= k.target]) / len(kpi_with_target) * 100
        if kpi_with_target else 0
    )

    departments = sorted(set(wm.department for wm in workflow_maps if wm.department))

    return {
        "org": org,
        "processes": processes,
        "opportunities": opportunities,
        "workflow_maps": workflow_maps,
        "architecture": architecture,
        "builds": builds,
        "kpis": kpis,
        "phases": phases,
        "departments": departments,
        "stats": {
            "process_count": len(processes),
            "opportunity_count": len(opportunities),
            "total_annual_hours": round(total_hours, 1),
            "completed_builds": completed_builds,
            "kpi_completion_pct": round(kpi_pct, 1),
            "workflow_map_count": len(workflow_maps),
        },
    }


@router.get("", response_class=HTMLResponse)
async def dashboard_overview(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    return templates.TemplateResponse("dashboard/index.html", {"request": request, **ctx})


@router.get("/process-maps", response_class=HTMLResponse)
async def dashboard_process_maps(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    return templates.TemplateResponse("dashboard/process_maps.html", {"request": request, **ctx})


@router.get("/opportunities", response_class=HTMLResponse)
async def dashboard_opportunities(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    return templates.TemplateResponse("dashboard/opportunities.html", {"request": request, **ctx})


@router.get("/architecture", response_class=HTMLResponse)
async def dashboard_architecture(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    return templates.TemplateResponse("dashboard/architecture.html", {"request": request, **ctx})


@router.get("/builds", response_class=HTMLResponse)
async def dashboard_builds(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    # Group builds by opportunity
    builds_by_opp = {}
    for b in ctx["builds"]:
        if b.opportunity_id not in builds_by_opp:
            builds_by_opp[b.opportunity_id] = []
        builds_by_opp[b.opportunity_id].append(b)
    return templates.TemplateResponse(
        "dashboard/builds.html",
        {"request": request, "builds_by_opp": builds_by_opp, **ctx},
    )


@router.get("/kpis", response_class=HTMLResponse)
async def dashboard_kpis(request: Request, db: Session = Depends(get_db)):
    ctx = _get_dashboard_context(db)
    return templates.TemplateResponse("dashboard/kpis.html", {"request": request, **ctx})


@router.post("/phases/{phase_id}/progress")
async def update_phase_progress(
    phase_id: int,
    progress_pct: float = Form(...),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    phase = db.query(ImplementationPhase).filter(ImplementationPhase.id == phase_id).first()
    if phase:
        phase.progress_pct = min(100, max(0, progress_pct))
        if status:
            phase.status = status
        db.commit()
    return HTMLResponse(f'<span class="progress-value">{phase.progress_pct:.0f}%</span>')
