import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KPI, KPIHistory

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.post("")
async def create_kpi(
    name: str = Form(...),
    value: float = Form(0),
    target: float = Form(0),
    unit: str = Form(""),
    department: str = Form(""),
    category: str = Form(""),
    db: Session = Depends(get_db),
):
    kpi = KPI(
        name=name,
        value=value,
        target=target,
        unit=unit,
        department=department,
        category=category,
    )
    db.add(kpi)
    db.commit()
    db.refresh(kpi)

    # Save initial history entry
    db.add(KPIHistory(kpi_id=kpi.id, value=value))
    db.commit()

    return RedirectResponse(url="/dashboard/kpis", status_code=303)


@router.patch("/{kpi_id}")
async def update_kpi(
    request: Request,
    kpi_id: int,
    db: Session = Depends(get_db),
):
    form = await request.form()
    new_value = float(form.get("value", 0))

    kpi = db.query(KPI).filter(KPI.id == kpi_id).first()
    if not kpi:
        return HTMLResponse("KPI not found", status_code=404)

    kpi.value = new_value
    kpi.updated_at = datetime.utcnow()
    db.add(KPIHistory(kpi_id=kpi.id, value=new_value))
    db.commit()
    db.refresh(kpi)

    history = (
        db.query(KPIHistory)
        .filter(KPIHistory.kpi_id == kpi_id)
        .order_by(KPIHistory.recorded_at)
        .all()
    )

    return templates.TemplateResponse(
        "partials/kpi_card.html",
        {"request": request, "kpi": kpi, "history": history},
    )


@router.delete("/{kpi_id}")
async def delete_kpi(kpi_id: int, db: Session = Depends(get_db)):
    db.query(KPIHistory).filter(KPIHistory.kpi_id == kpi_id).delete()
    db.query(KPI).filter(KPI.id == kpi_id).delete()
    db.commit()
    return HTMLResponse("")
