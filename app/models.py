from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(255))
    org_chart_text = Column(Text)
    tool_stack_json = Column(JSON, default=list)
    bottlenecks_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    step = Column(String(50), nullable=False)  # discovery|workflow|audit|arch|build
    role = Column(String(20), nullable=False)  # user|assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(255))
    description = Column(Text)
    time_cost_hours_per_week = Column(Float, default=0)
    rank = Column(Integer, default=0)

    workflow_maps = relationship("WorkflowMap", back_populates="process", foreign_keys="WorkflowMap.process_id")


class WorkflowMap(Base):
    __tablename__ = "workflow_maps"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(255))
    plain_english_input = Column(Text)
    mermaid_diagram = Column(Text)
    flagged_handoffs_json = Column(JSON, default=list)
    flagged_redundancies_json = Column(JSON, default=list)
    automation_triggers_json = Column(JSON, default=list)
    process_id = Column(Integer, ForeignKey("processes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    process = relationship("Process", back_populates="workflow_maps", foreign_keys=[process_id])
    opportunities = relationship("AutomationOpportunity", back_populates="workflow_map")


class AutomationOpportunity(Base):
    __tablename__ = "automation_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer, default=0)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    roi_score = Column(Float, default=0)
    complexity = Column(String(20))  # low|medium|high
    build_time_days = Column(Float, default=0)
    annual_hours_saved = Column(Float, default=0)
    platform_recommendation = Column(String(100))
    status = Column(String(50), default="pending")  # pending|in_progress|completed
    workflow_map_id = Column(Integer, ForeignKey("workflow_maps.id"), nullable=True)

    workflow_map = relationship("WorkflowMap", back_populates="opportunities")
    builds = relationship("WorkflowBuild", back_populates="opportunity")


class SystemArchitecture(Base):
    __tablename__ = "system_architectures"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text)
    mermaid_diagram = Column(Text)
    agents_json = Column(JSON, default=list)
    linear_flows_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowBuild(Base):
    __tablename__ = "workflow_builds"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("automation_opportunities.id"))
    platform = Column(String(50))  # n8n|zapier|make|python
    workflow_json = Column(Text)
    documentation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    opportunity = relationship("AutomationOpportunity", back_populates="builds")


class KPI(Base):
    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    value = Column(Float, default=0)
    target = Column(Float, default=0)
    unit = Column(String(50))
    department = Column(String(255))
    category = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = relationship("KPIHistory", back_populates="kpi", order_by="KPIHistory.recorded_at")


class KPIHistory(Base):
    __tablename__ = "kpi_history"

    id = Column(Integer, primary_key=True, index=True)
    kpi_id = Column(Integer, ForeignKey("kpis.id"))
    value = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    kpi = relationship("KPI", back_populates="history")


class ImplementationPhase(Base):
    __tablename__ = "implementation_phases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending")  # pending|in_progress|completed
    progress_pct = Column(Float, default=0)
    phase_order = Column(Integer, default=0)
    tasks_json = Column(JSON, default=list)
