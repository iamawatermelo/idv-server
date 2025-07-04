from datetime import datetime, date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import ARRAY, Field, Relationship, SQLModel, String

from idv_server.enums import (
    AuthenticityType,
    OwnershipType,
    TicketVerificationVerdict,
    TicketStage,
    UserVerdictType,
)


class IssuerModel(SQLModel, table=True):
    __tablename__ = "issuer"

    id: int | None = Field(default=None, primary_key=True)
    uuid: UUID = Field(default=uuid4)

    name: str

    hct_root_tone: int | None
    bg_url: str | None
    icon_url: str | None
    favicon_url: str | None

    default_claim_expiration_time: int = 3600
    default_verification_expiration_time: int = 86400
    default_ticket_expiration_time: int = 604800

    tickets: list["TicketModel"] = Relationship(back_populates="issuer")


class BasicInformationModel(SQLModel, table=True):
    __tablename__ = "basicinformation"

    id: int | None = Field(default=None, primary_key=True)

    first_name: str
    last_name: str
    date_of_birth: date
    country_of_primary_residence: str

    ticket_id: int = Field(foreign_key="ticket.id", unique=True)
    ticket: "TicketModel" = Relationship(back_populates="basic_information")


class VerificationInformationModel(SQLModel, table=True):
    __tablename__ = "verificationinformation"

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
    ticket: "TicketModel" = Relationship(back_populates="verification_information")


class MetadataModel(SQLModel, table=True):
    __tablename__ = "metadata"

    id: int | None = Field(default=None, primary_key=True)

    timestamp: datetime
    source: str
    message: str
    details: dict[str, Any] = Field(sa_column=Column(JSONB))

    ticket_id: int = Field(foreign_key="ticket.id")
    ticket: "TicketModel" = Relationship(back_populates="metadata_entries")


class TicketModel(SQLModel, table=True):
    __tablename__ = "ticket"

    id: int | None = Field(default=None, primary_key=True)
    uuid: UUID

    issuer_id: int = Field(foreign_key="issuer.id")
    issuer: IssuerModel = Relationship(back_populates="tickets")

    issued_at: datetime
    claim_expires_at: datetime
    verification_expires_at: datetime
    ticket_expires_at: datetime

    stage: TicketStage = TicketStage.NOT_CLAIMED
    user_verdict: str | None = None
    user_verdict_type: UserVerdictType | None = None

    acceptable_authenticity: list[AuthenticityType] = Field(sa_column=Column(ARRAY(String)))
    acceptable_ownership: list[OwnershipType] = Field(sa_column=Column(ARRAY(String)))

    basic_information: BasicInformationModel | None = Relationship(back_populates="ticket")

    verification_information: VerificationInformationModel | None = Relationship(back_populates="ticket")

    metadata_entries: list[MetadataModel] = Relationship(back_populates="ticket")
