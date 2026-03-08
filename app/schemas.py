from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class OrgSetup(BaseModel):
    name: str
    industry: str
    org_chart_text: str = ""
    tool_stack: str = ""  # comma-separated, converted to list
    bottlenecks: str = ""  # newline-separated, converted to list


class DiscoveryReply(BaseModel):
    message: str


class WorkflowMapRequest(BaseModel):
    department: str
    plain_english: str
    process_id: Optional[int] = None


class BuildRequest(BaseModel):
    opportunity_id: int


class KPICreate(BaseModel):
    name: str
    value: float = 0
    target: float = 0
    unit: str = ""
    department: str = ""
    category: str = ""


class KPIUpdate(BaseModel):
    value: float


class PhaseProgressUpdate(BaseModel):
    progress_pct: float
    status: Optional[str] = None
