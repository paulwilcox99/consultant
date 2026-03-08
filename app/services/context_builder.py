import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Organization, ConversationMessage, Process,
    WorkflowMap, AutomationOpportunity, SystemArchitecture,
)


def get_org_context(db: Session) -> str:
    org = db.query(Organization).first()
    if not org:
        return "No organization data yet."
    tools = ", ".join(org.tool_stack_json or [])
    bottlenecks = "; ".join(org.bottlenecks_json or [])
    return (
        f"Organization: {org.name}\n"
        f"Industry: {org.industry}\n"
        f"Tool Stack: {tools}\n"
        f"Top Bottlenecks: {bottlenecks}\n"
        f"Org Chart:\n{org.org_chart_text or 'Not provided'}"
    )


def get_conversation_context(db: Session, step: str) -> str:
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.step == step)
        .order_by(ConversationMessage.created_at)
        .all()
    )
    if not messages:
        return ""
    lines = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n\n".join(lines)


def get_process_context(db: Session) -> str:
    processes = db.query(Process).order_by(Process.rank).all()
    if not processes:
        return "No processes identified yet."
    lines = ["Identified Processes:"]
    for p in processes:
        lines.append(
            f"- [{p.rank}] {p.name} ({p.department}): "
            f"{p.time_cost_hours_per_week}h/week — {p.description}"
        )
    return "\n".join(lines)


def get_workflow_context(db: Session, department: Optional[str] = None) -> str:
    query = db.query(WorkflowMap)
    if department:
        query = query.filter(WorkflowMap.department == department)
    maps = query.order_by(WorkflowMap.created_at).all()
    if not maps:
        return "No workflow maps yet."
    lines = ["Workflow Maps:"]
    for wm in maps:
        lines.append(f"\nDepartment: {wm.department}")
        lines.append(f"Description: {wm.plain_english_input}")
        lines.append(f"Handoffs: {json.dumps(wm.flagged_handoffs_json or [])}")
        lines.append(f"Redundancies: {json.dumps(wm.flagged_redundancies_json or [])}")
        lines.append(f"Triggers: {json.dumps(wm.automation_triggers_json or [])}")
    return "\n".join(lines)


def get_opportunities_context(db: Session) -> str:
    opps = db.query(AutomationOpportunity).order_by(AutomationOpportunity.rank).all()
    if not opps:
        return "No automation opportunities identified yet."
    lines = ["Automation Opportunities:"]
    for o in opps:
        lines.append(
            f"[{o.rank}] {o.title} — ROI: {o.roi_score}, "
            f"Complexity: {o.complexity}, "
            f"Build: {o.build_time_days}d, "
            f"Saves: {o.annual_hours_saved}h/yr, "
            f"Platform: {o.platform_recommendation}"
        )
        if o.description:
            lines.append(f"    {o.description}")
    return "\n".join(lines)


def build_audit_context(db: Session) -> str:
    """Full context for Step 3 audit prompt."""
    return (
        get_org_context(db) + "\n\n"
        + get_process_context(db) + "\n\n"
        + get_workflow_context(db)
    )


def build_architecture_context(db: Session) -> str:
    """Full context for Step 4 architecture prompt."""
    org = db.query(Organization).first()
    tools = ", ".join(org.tool_stack_json or []) if org else ""
    return (
        get_org_context(db) + "\n\n"
        + get_opportunities_context(db) + "\n\n"
        f"Available Tools/Platforms: {tools}"
    )


def build_build_context(db: Session, opportunity_id: int) -> str:
    """Full context for Step 5 build prompt."""
    opp = db.query(AutomationOpportunity).filter(AutomationOpportunity.id == opportunity_id).first()
    if not opp:
        return "Opportunity not found."
    arch = db.query(SystemArchitecture).first()
    arch_desc = arch.description if arch else "Not designed yet."
    return (
        get_org_context(db) + "\n\n"
        f"Target Opportunity:\n"
        f"  Title: {opp.title}\n"
        f"  Description: {opp.description}\n"
        f"  Platform Recommendation: {opp.platform_recommendation}\n"
        f"  Complexity: {opp.complexity}\n"
        f"  Annual Hours Saved: {opp.annual_hours_saved}\n\n"
        f"System Architecture Summary:\n{arch_desc}"
    )
