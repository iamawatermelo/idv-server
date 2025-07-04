from datetime import date, datetime, timedelta
import time
from typing import TYPE_CHECKING, Annotated, Any, Literal, NewType, TypeAlias
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
import strawberry
import strawberry.asgi
from uuid import UUID
from strawberry.field_extensions import InputMutationExtension
from strawberry.scalars import JSON

from idv_server.config import config
from idv_server.auth import Unauthorized, authorize
from idv_server.enums import (
    AuthenticityType,
    OwnershipType,
    TicketVerificationVerdict,
    TicketStage,
    UserVerdictType,
)
from idv_server.env import Env
from idv_server.models import ApplicationModel, TicketModel

ID = strawberry.scalar(
    NewType("ID", UUID),
    serialize=lambda u: str(u),
    parse_value=lambda u: UUID(hex=u),
)

if TYPE_CHECKING:
    ID: TypeAlias = UUID


def headers(info: strawberry.Info):
    """
    Extract authentication headers from a strawberry.Info object
    """
    
    if config.auth is None:
        return {}
    
    return {
        k: v
        for k, v in info.context["request"].headers.items()
        if k in config.auth.forwarded_headers
    }


@strawberry.type
class Application:
    name: str

    hct_root_tone: int | None
    bg_url: str | None
    icon_url: str | None
    favicon_url: str | None


@strawberry.type
class MetadataEntry:
    timestamp: datetime
    source: str
    message: str
    details: JSON


@strawberry.type
class UserData:
    authenticity: AuthenticityType
    ownership: OwnershipType

    first_name: str
    last_name: str
    date_of_birth: date


@strawberry.type
class TicketVerificationInformation:
    verifier: str | None

    verdict: TicketVerificationVerdict
    verdict_reason: str | None
    verdict_human_reason: str | None

    user_data: UserData | None

    metadata: list[MetadataEntry]


@strawberry.type
class Ticket:
    db_id: strawberry.Private[UUID]
    id: ID
    
    issuer_id: strawberry.Private[UUID]
    issuer: Application

    issued_at: datetime

    # Deadline for claiming the ticket
    claim_expires_at: datetime

    # Deadline for verification
    verification_expires_at: datetime

    # When the ticket will be deleted
    ticket_expires_at: datetime | None

    stage: TicketStage
    verdict: str | None
    verdict_type: UserVerdictType | None

    verification_options: list[str] | None

    # Only available to the issuer, not the user
    @strawberry.field
    async def verification_information(
        self,
        info: strawberry.Info
    ) -> TicketVerificationInformation:
        await authorize(
            "READ",
            f"/ticket/{id}/verificationInformation",
            headers=headers(info),
            authorized_subject=None
        )
        
        pass


@strawberry.type
class StartBasicVerificationResult:
    authentication_token: str

    ticket: Ticket


@strawberry.type
class StartVerificationResult:
    verification_url: str
    verification_ticket: str
    verification_authentication_token: str

    ticket: Ticket


@strawberry.type
class Query:
    @strawberry.field
    async def ticket(self, info: strawberry.Info, id: ID) -> Ticket:
        await authorize(
            "READ",
            f"/ticket/{id}",
            headers=headers(info),
            authorized_subject=None
        )
        
        pass


@strawberry.input
class TicketOptionsInput:
    acceptable_authenticity: list[AuthenticityType]
    acceptable_ownership: list[OwnershipType]


@strawberry.input
class BasicInformation:
    first_name: str
    last_name: str
    date_of_birth: date
    country_of_primary_residence: str


@strawberry.input
class MetadataEntryInput:
    timestamp: datetime
    source: str
    message: str
    details: JSON


@strawberry.input
class UserDataInput:
    authenticity: AuthenticityType
    ownership: OwnershipType

    first_name: str
    last_name: str
    date_of_birth: date


@strawberry.type
class Mutation:
    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def create_ticket(
        self,
        info: strawberry.Info,
        issuer: ID,
        ticket_options: TicketOptionsInput
    ) -> Ticket:
        await authorize(
            "MODIFY",
            f"/issuer/{issuer}/createTicket",
            headers=headers(info),
            authorized_subject=str(issuer) if issuer else None
        )
        
        env = Env.ctx()
        
        async with env.db.begin() as tx, AsyncSession(tx) as session:
            issuer_model = (await session.execute(
                select(ApplicationModel)
                .where(ApplicationModel.uuid == issuer)
            )).scalars().one_or_none
            
            if not issuer_model:
                raise ValueError("Issuer not found")
        
            now = datetime.now()
            
            ticket = TicketModel(
                issuer_id=issuer,
                issued_at=now,
                claim_expires_at=now + timedelta(seconds=issuer_model.default_claim_expiration_time),
                verification_expires_at=now + timedelta(seconds=issuer_model.default_verification_expiration_time),
                ticket_expires_at=now + timedelta(seconds=issuer_model.default_ticket_expiration_time)
            )
            
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            
            return Ticket(
                
            )
        

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def start_basic_verification(
        self,
        info: strawberry.Info,
        ticket: ID
    ) -> StartBasicVerificationResult:
        await authorize(
            "MODIFY",
            f"/ticket/{ticket}/startBasicVerification",
            headers=headers(info),
            authorized_subject=None
        )
        
        pass

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def submit_basic_information(
        self,
        info: strawberry.Info,
        ticket: ID,
        basic_information: BasicInformation
    ) -> StartVerificationResult:
        await authorize(
            "MODIFY",
            f"/ticket/{ticket}/submitBasicInformation",
            headers=headers(info),
            authorized_subject=None
        )
        
        pass

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def update_verification_ticket(
        self,
        info: strawberry.Info,
        verification_ticket: ID,
        message: str,
        metadata: list[MetadataEntryInput],
    ) -> Ticket:
        await authorize(
            "MODIFY",
            f"/verificationTicket/{verification_ticket}/updateVerificationTicket",
            headers=headers(info),
            authorized_subject=None # TODO
        )
        
        pass

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def finalise_verification_ticket(
        self,
        info: strawberry.Info,
        verification_ticket: ID,
        verdict: TicketVerificationVerdict,
        metadata: list[MetadataEntryInput],
        user_data: UserDataInput,
    ) -> Ticket:
        await authorize(
            "MODIFY",
            f"/verificationTicket/{verification_ticket}/finalizeVerificationTicket",
            headers=headers(info),
            authorized_subject=None # TODO
        )
        
        pass


schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql = strawberry.asgi.GraphQL(schema=schema)
