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


class BasicInformation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    first_name: str
    last_name: str
    date_of_birth: date
    country_of_primary_residence: str
    
    ticket_id: int = Field(foreign_key="ticket.id", unique=True)
    ticket: Ticket = Relationship(back_populates="basic_information")


class VerificationInformation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    verifier: str
    verdict: TicketVerificationVerdict
    verdict_reason: str
    verdict_human_reason: str | None
    
    authenticity: AuthenticityType | None 
    ownership: OwnershipType | None
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None
    
    ticket_id: int = Field(foreign_key="ticket.id", unique=True)
    ticket: Ticket = Relationship(back_populates="verification_information")


class Metadata(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    
    timestamp: datetime
    source: str
    message: str
    details: dict[str, Any] = Field(sa_column=Column(JSONB))
    
    ticket_id: int = Field(foreign_key="ticket.id")
    ticket: Ticket = Relationship(back_populates="metadata")


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
    
    basic_information: BasicInformation | None = Relationship(back_populates="ticket")
    
    verification_information: VerificationInformation | None = Relationship(back_populates="ticket")

    metadata_entries: list[Metadata] = Relationship(back_populates="ticket")