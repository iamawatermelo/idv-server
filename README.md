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