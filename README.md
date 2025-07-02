<h1>
    <picture height="64">
        <source
            srcset="idv-logo-light.svg"
            media="(prefers-color-scheme: dark)"
        />
        <source
            srcset="idv-logo-black.svg"
            media="(prefers-color-scheme: light), (prefers-color-scheme: no-preference)"
        />
        <img src="idv-logo-black.svg" height="16"/>
    </picture>
    <br>
    IDV server
</h1>

Check back later.

```mermaid
sequenceDiagram
    participant User
    participant App
    participant IDV as IDV Server
    participant EP as ePassport IDV Backend

    App ->> IDV: (gql) createTicket()
    IDV -->> App: Created ticket idv.srh.dog/ticket/...
    App ->> User: Redirect to idv.srh.dog/ticket/...
    User ->> IDV: (gql) startVerification()
    IDV -->> User: Authentication cookie

    User ->> IDV: (gql) submitBasicInformation()
    IDV -->> User: Verification options: Manual, ePassport, Aadhaar (unsupported in region)

    User ->> IDV: (gql) beginVerification(option: "ePassport")
    
    IDV ->>+ EP: (gql) createVerificationTicket(...)
    EP -->> IDV: Created ticket ...

    IDV -->> User: Verification ticket: ..., service URL: epassport.idv.srh.dog/api/v0
    
    alt ePassport success
        User ->> EP: Submit ePassport data
        EP ->> IDV: (gql) finalizeVerificationTicket(isError: false, isFatal: false, metadata: ..., userData: ...)
    else ePassport failure due to user error
        User ->> EP: Submit failure reason
        EP ->> IDV: (gql) finalizeVerificationTicket(isError: true, isFatal: false, metadata: ...)
    else ePassport failure due to fraud 
        User ->> EP: Submit ePassport data
        EP ->>- IDV: (gql) finalizeVerificationTicket(isError: true, isFatal: true, metadata: ...)
    end

    alt Verification webhooks not supported
        loop Poll verification status
            App ->> IDV: (gql) ticket(...)
            IDV -->> App: User verified/not verified
        end
    else
        IDV ->> App: User verified with status ...
    end
```

## Authentication

Authentication is wide and varied, and so it is left up to implementors
of IDV. idv-server is designed to delegate authentication and
authorization to a third-party Policy Decision Point (PDP).

### API

idv-server will forward the headers in `auth_headers` and send a request
to the `auth_pdp_endpoint` to determine whether access should be
allowed.

```
GET /createTicket HTTP/1.1
Authorization: eyXXXXXX
.. other forwarded headers ..
```

idv-server will accept the request if a 200 or 204 is returned, and
reject otherwise.

### Routes

#### Queries

> [!NOTE]
> idv-server will include an `X-Issuer-Id` header, which includes the
> issuer of the ticket.

- `ticket(id: $id)` -> `GET /ticket/$id`
  **Note:** Should be public.

- `ticket(id: $id) { verificationInformation }` -> `GET /ticket/$id/verificationInformation`
  **Note:** Should only be available to the issuer.

#### Mutations

- `createTicket(issuer: $id)` -> `POST /issuer/$id/createTicket`
  **Note:** Should only be available to issuers.
  
> [!NOTE]
> idv-server will include an `X-Issuer-Id` header.
  
- `startBasicVerification(ticket: $id)` -> `POST /ticket/$id/startBasicVerification`
  **Note:** Should be public. idv-server will also verify the
  Authorization header to ensure that it matches the token associated
  with the ticket.

- `submitBasicInformation(ticket: $id)` -> `POST /ticket/$id/submitBasicInformation`
  **Note:** Should be public. idv-server will also verify the
  Authorization header to ensure that it matches the token associated
  with the ticket.

> [!NOTE]
> idv-server will include an `X-Verifier-Id` header.

- `updateVerificationTicket(ticket: $id)` -> `POST /verificationTicket/$id/updateVerificationTicket`
  **Note:** Should only be available to the verifier that the ticket
  was issued to.

- `finalizeVerificationTicket(ticket: $id)` -> `POST /verificationTicket/$id/finalizeVerificationTicket`
  **Note:** Should only be available to the verifier that the ticket
  was issued to.