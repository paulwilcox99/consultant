from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import engine
from app.models import Base

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Organizational Efficiency Consultant")

# Static files
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Templates (shared across routers)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Import and include routers
from app.routers import home, discovery, workflow, audit, architecture, build, dashboard, kpis

app.include_router(home.router)
app.include_router(discovery.router, prefix="/discovery")
app.include_router(workflow.router, prefix="/workflow")
app.include_router(audit.router, prefix="/audit")
app.include_router(architecture.router, prefix="/architecture")
app.include_router(build.router, prefix="/build")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(kpis.router, prefix="/kpis")
