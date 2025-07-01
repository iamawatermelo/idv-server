from __future__ import annotations
from datetime import datetime, date
import enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Field, Relationship, SQLModel

from idv_server.enums import (
    AuthenticityType,
    OwnershipType,
    TicketVerificationVerdict,
    TicketStage,
    UserVerdictType,
)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    name: str
    
    hct_root_tone: int | None
    bg_url: str | None
    icon_url: str | None
    favicon_url: str | None
    
    tickets: list[Ticket] = Relationship(back_populates="issuer")


class Ticket(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ticket_id: UUID = Field(default=uuid4)
    
    issuer_id: int = Field(foreign_key="application.id")
    issuer: Application = Relationship(back_populates="tickets")
    
    issued_at: datetime
    claim_expires_at: datetime
    verification_expires_at: datetime
    ticket_expires_at: datetime
    
    stage: TicketStage
    user_verdict: str | None
    user_verdict_type: UserVerdictType | None
    
    user_first_name: str | None
    user_last_name: str | None
    user_date_of_birth: date
    user_country_of_primary_residence: str
    
    authentication_token: str | None
    
    verifier: str | None
    verdict: TicketVerificationVerdict
    verdict_reason: str | None
    verdict_human_reason: str | None
    verified_first_name: str | None
    verified_last_name: str | None
    verified_date_of_birth: str | None
    metadata: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))