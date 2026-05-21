from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class WorkflowStatus(str, enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    APPROVAL_REQUIRED = 'approval_required'
    COMPLETED = 'completed'
    FAILED = 'failed'
    ESCALATED = 'escalated'


class Workflow(Base):
    __tablename__ = 'workflows'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    workflow_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    trigger_source = Column(String(128))
    severity = Column(String(32), default='medium')
    status = Column(SAEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    assigned_to = Column(String(128))
    metadata_json = Column('metadata', JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    steps = relationship('WorkflowStep', back_populates='workflow', cascade='all, delete-orphan')


class WorkflowStep(Base):
    __tablename__ = 'workflow_steps'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False)
    step_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(32), default='pending')
    requires_approval = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    payload = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workflow = relationship('Workflow', back_populates='steps')
