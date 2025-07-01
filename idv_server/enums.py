import enum
import strawberry


@strawberry.enum
class AuthenticityType(enum.Enum):
    # The document has been cross-checked by a government's signature
    # or a government database.
    STRONG = "STRONG"

    # The document was visually inspected.
    MANUAL = "MANUAL"

    # The document was not verified at all.
    NOT_VERIFIED = "NOT_VERIFIED"


@strawberry.enum
class OwnershipType(enum.Enum):
    # Liveness checking and facial recognition was used to ensure the
    # document belongs to them.
    STRONG = "STRONG"

    # The document was manually matched to a user's face.
    MANUAL = "MANUAL"

    # The document was not verified.
    NOT_VERIFIED = "NOT_VERIFIED"


@strawberry.enum
class TicketVerificationVerdict(enum.Enum):
    NOT_FINISHED = "NOT_FINISHED"
    ABANDONED = "ABANDONED"

    # Rejected temporarily means the user should be able to resubmit.
    REJECTED_TEMPORARILY = "REJECTED_TEMPORARILY"

    # Rejected permanently means that the user should be flagged for
    # fraudulent behaviour.
    REJECTED_PERMANENTLY = "REJECTED_PERMANENTLY"

    ACCEPTED = "ACCEPTED"


@strawberry.enum
class TicketStage(enum.Enum):
    NOT_CLAIMED = "NOT_CLAIMED"
    AUTH_ISSUED = "AUTH_ISSUED"
    BASIC_INFORMATION_SUBMITTED = "BASIC_INFORMATION_SUBMITTED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_FINISHED = "VERIFICATION_FINISHED"


@strawberry.enum
class UserVerdictType(enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
