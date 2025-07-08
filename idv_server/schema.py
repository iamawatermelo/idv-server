from datetime import date, datetime, timedelta
import time
from typing import TYPE_CHECKING, Annotated, Any, Literal, NewType, Self, TypeAlias
from graphql import GraphQLError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
import strawberry
import strawberry.asgi
from uuid import UUID, uuid4
from strawberry.field_extensions import InputMutationExtension
from strawberry.scalars import JSON
import hashlib

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
from idv_server.models import BasicInformationModel, IssuerModel, TicketModel, TokenModel, VerificationInformationModel

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

def hash_token(info: strawberry.Info, ticket: ID):
    request: Request = info.context["request"]
    auth_header = request.headers.get("Authorization")
    
    if auth_header is None:
        raise Unauthorized()
    
    auth_header = auth_header.replace("Bearer ", "")
    
    try:
        token = UUID(hex=auth_header.strip())
    except ValueError:
        raise Unauthorized()
    
    hashed_token = hashlib.sha256(
        ticket.bytes + token.bytes
    ).hexdigest()
    
    return hashed_token

@strawberry.type
class Issuer:
    id: ID
    name: str

    hct_root_tone: int | None
    bg_url: str | None
    icon_url: str | None
    favicon_url: str | None

    default_claim_expiration_time: int
    default_verification_expiration_time: int
    default_ticket_expiration_time: int

    @classmethod
    def from_orm(cls, issuer_model: IssuerModel) -> Self:
        """
        Convert an IssuerModel to an Issuer GraphQL type
        """

        return cls(
            id=issuer_model.uuid,
            name=issuer_model.name,
            hct_root_tone=issuer_model.hct_root_tone,
            bg_url=issuer_model.bg_url,
            icon_url=issuer_model.icon_url,
            favicon_url=issuer_model.favicon_url,
            default_claim_expiration_time=issuer_model.default_claim_expiration_time,
            default_verification_expiration_time=issuer_model.default_verification_expiration_time,
            default_ticket_expiration_time=issuer_model.default_ticket_expiration_time,
        )


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
    verdict: TicketVerificationVerdict

    verifier: str | None = None

    verdict_reason: str | None = None
    verdict_human_reason: str | None = None

    user_data: UserData | None = None

    metadata: list[MetadataEntry] = []

    @classmethod
    def from_orm(
        cls, verification_information_model: VerificationInformationModel
    ) -> Self:
        """
        Convert a VerificationInformationModel to a TicketVerificationInformation GraphQL type
        """

        # Create UserData if we have the required fields
        user_data = None
        if (
            verification_information_model.authenticity is not None
            and verification_information_model.ownership is not None
            and verification_information_model.first_name is not None
            and verification_information_model.last_name is not None
            and verification_information_model.date_of_birth is not None
        ):
            user_data = UserData(
                authenticity=verification_information_model.authenticity,
                ownership=verification_information_model.ownership,
                first_name=verification_information_model.first_name,
                last_name=verification_information_model.last_name,
                date_of_birth=verification_information_model.date_of_birth,
            )

        # Convert metadata entries
        metadata = []
        if (
            verification_information_model.ticket
            and verification_information_model.ticket.metadata_entries
        ):
            metadata = [
                MetadataEntry(
                    timestamp=entry.timestamp,
                    source=entry.source,
                    message=entry.message,
                    details=entry.details,
                )
                for entry in verification_information_model.ticket.metadata_entries
            ]

        return cls(
            verdict=verification_information_model.verdict,
            verifier=verification_information_model.verifier,
            verdict_reason=verification_information_model.verdict_reason,
            verdict_human_reason=verification_information_model.verdict_human_reason,
            user_data=user_data,
            metadata=metadata,
        )


@strawberry.type
class Ticket:
    db_id: strawberry.Private[UUID]
    id: ID

    issuer_id: strawberry.Private[UUID]

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

    verification_information_id: strawberry.Private[int]

    # Only available to the issuer, not the user
    @strawberry.field
    async def verification_information(
        self, info: strawberry.Info
    ) -> TicketVerificationInformation | None:
        """
        Fetch verification information from this ticket. Available to
        issuers only.
        """

        await authorize(
            "READ",
            f"/ticket/{id}/verificationInformation",
            headers=headers(info),
            authorized_subject=None,
        )

        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            verification_information_model = (
                (
                    await session.execute(
                        select(VerificationInformationModel).where(
                            VerificationInformationModel.ticket_id == self.db_id
                        )
                    )
                )
                .scalars()
                .one_or_none()
            )

            if verification_information_model is None:
                return None

            return TicketVerificationInformation.from_orm(
                verification_information_model
            )

    @strawberry.field
    async def issuer(self) -> Issuer:
        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            return Issuer.from_orm(session.get(IssuerModel, self.issuer_id))

    @classmethod
    def from_orm(cls, ticket_model: TicketModel) -> Self:
        """
        Convert a TicketModel to a Ticket GraphQL type
        """

        return cls(
            db_id=ticket_model.id,
            id=ticket_model.uuid,
            issuer_id=ticket_model.issuer_id,
            issued_at=ticket_model.issued_at,
            claim_expires_at=ticket_model.claim_expires_at,
            verification_expires_at=ticket_model.verification_expires_at,
            ticket_expires_at=ticket_model.ticket_expires_at,
            stage=ticket_model.stage,
            verdict=ticket_model.user_verdict,
            verdict_type=ticket_model.user_verdict_type,
        )


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
            "READ", f"/ticket/{id}", headers=headers(info), authorized_subject=None
        )

        env = Env().ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            ticket_model = (
                (
                    await session.execute(
                        select(TicketModel).where(TicketModel.uuid == id)
                    )
                )
                .scalars()
                .one_or_none()
            )

            if not ticket_model:
                raise ValueError("Issuer not found")

            return Ticket.from_orm(ticket_model)

    @strawberry.field
    async def issuer(self, info: strawberry.Info, id: ID) -> Issuer:
        await authorize(
            "READ", f"/issuer/{id}", headers=headers(info), authorized_subject=None
        )

        env = Env().ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            issuer_model = (
                (
                    await session.execute(
                        select(IssuerModel).where(IssuerModel.uuid == id)
                    )
                )
                .scalars()
                .one_or_none()
            )

            if not issuer_model:
                raise ValueError("Issuer not found")

            return Issuer.from_orm(issuer_model)


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
    async def create_issuer(
        self,
        info: strawberry.Info,
        name: str,
        hct_root_tone: int | None = None,
        bg_url: str | None = None,
        icon_url: str | None = None,
        favicon_url: str | None = None,
        default_claim_expiration_time: int = 3600,
        default_verification_expiration_time: int = 86400,
        default_ticket_expiration_time: int = 604800,
    ) -> Issuer:
        await authorize(
            "MODIFY", "/createIssuer", headers=headers(info), authorized_subject=None
        )

        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            issuer = IssuerModel(
                uuid=uuid4(),
                name=name,
                hct_root_tone=hct_root_tone,
                bg_url=bg_url,
                icon_url=icon_url,
                favicon_url=favicon_url,
                default_claim_expiration_time=default_claim_expiration_time,
                default_verification_expiration_time=default_verification_expiration_time,
                default_ticket_expiration_time=default_ticket_expiration_time,
            )

            session.add(issuer)
            await session.commit()
            await session.refresh(issuer)

            return Issuer.from_orm(issuer)

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def create_ticket(
        self, info: strawberry.Info, issuer: ID, ticket_options: TicketOptionsInput
    ) -> Ticket:
        await authorize(
            "MODIFY",
            f"/issuer/{issuer}/createTicket",
            headers=headers(info),
            authorized_subject=str(issuer) if issuer else None,
        )

        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            issuer_model = (
                (
                    await session.execute(
                        select(IssuerModel).where(IssuerModel.uuid == issuer)
                    )
                )
                .scalars()
                .one_or_none()
            )

            if not issuer_model:
                raise ValueError("Issuer not found")

            now = datetime.now()

            ticket = TicketModel(
                uuid=uuid4(),
                issuer_id=issuer_model.id,
                issued_at=now,
                claim_expires_at=now
                + timedelta(seconds=issuer_model.default_claim_expiration_time),
                verification_expires_at=now
                + timedelta(seconds=issuer_model.default_verification_expiration_time),
                ticket_expires_at=now
                + timedelta(seconds=issuer_model.default_ticket_expiration_time),
                acceptable_authenticity=[
                    x.value for x in ticket_options.acceptable_authenticity
                ],
                acceptable_ownership=[
                    x.value for x in ticket_options.acceptable_ownership
                ],
            )

            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)

            return Ticket.from_orm(ticket)

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def start_basic_verification(
        self, info: strawberry.Info, ticket: ID
    ) -> StartBasicVerificationResult:
        await authorize(
            "MODIFY",
            f"/ticket/{ticket}/startBasicVerification",
            headers=headers(info),
            authorized_subject=None,
        )

        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            ticket_model = (
                (
                    await session.execute(
                        update(TicketModel)
                            .where(TicketModel.uuid == ticket)
                            .where(TicketModel.stage == TicketStage.NOT_CLAIMED)
                            .where(TicketModel.claim_expires_at > datetime.now())
                            .values(stage=TicketStage.AUTH_ISSUED)
                            .returning(TicketModel)
                    )
                ).scalar_one_or_none()
            )
            
            if ticket_model is None:
                raise GraphQLError("invalid state change: ticket doesn't exist, was already claimed or the claim period has expired")
            
            ticket_model.stage = TicketStage.AUTH_ISSUED
            
            token = uuid4()
            hashed_token = hashlib.sha256(ticket_model.uuid.bytes + token.bytes).hexdigest()
            
            session.add(TokenModel(
                hashed_token=hashed_token,
                ticket_id=ticket_model.id
            ))
            
            await session.commit()
            await session.refresh(ticket_model)
            
            # TODO: Implement session resumption
            
            return StartBasicVerificationResult(
                authentication_token=token.hex,
                ticket=Ticket.from_orm(ticket_model)
            )

    @strawberry.mutation(extensions=[InputMutationExtension()])
    async def submit_basic_information(
        self, info: strawberry.Info, ticket: ID, basic_information: BasicInformation
    ) -> SubmitBasicInformationResult:
        await authorize(
            "MODIFY",
            f"/ticket/{ticket}/submitBasicInformation",
            headers=headers(info),
            authorized_subject=None,
        )
        
        hashed_token = hash_token(info, ticket)
        
        env = Env.ctx()

        async with env.db.begin() as tx, AsyncSession(tx) as session:
            ticket_model = (
                (
                    await session.execute(
                        update(TicketModel)
                            .where(TicketModel.verification_expires_at > datetime.now())
                            .where(TicketModel.stage == TicketStage.AUTH_ISSUED)
                            .where(TicketModel.id.in_(
                                select(TokenModel.ticket_id)
                                    .where(TokenModel.hashed_token == hashed_token)
                            ))
                            .values(stage=TicketStage.BASIC_INFORMATION_SUBMITTED)
                            .returning(TicketModel)
                    )
                ).scalar_one_or_none()
            )
            
            if ticket_model is None or ticket_model.uuid != ticket:
                raise GraphQLError("invalid state change: unauthenticated/unauthorized, ticket doesn't exist or ticket expired")
        
            session.add(BasicInformationModel(
                first_name=basic_information.first_name,
                last_name=basic_information.last_name,
                date_of_birth=basic_information.date_of_birth,
                country_of_primary_residence=basic_information.country_of_primary_residence,
                ticket_id=ticket_model.id
            ))
            
            await session.commit()
            
            #return StartBsas.

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
            authorized_subject=None,  # TODO
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
            authorized_subject=None,  # TODO
        )

        pass


schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql = strawberry.asgi.GraphQL(schema=schema)
