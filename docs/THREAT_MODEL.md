# Threat Model for StyleDNA

## Scope and assets

StyleDNA handles sensitive personal data, including body measurements, wardrobe media, and user preference history. The highest-risk assets are:

- Body media and derived shape metadata
- Wardrobe images and cutouts
- User authentication secrets and refresh tokens
- LLM and search provider outputs used for personalization and outfit generation
- Audit logs and user profile data

This threat model follows a STRIDE-lite structure focused on the security requirements from Phase 1 and the existing automated tests in the repository.

## STRIDE-lite summary

| Threat | Asset | Primary risk | Mitigation |
|---|---|---|---|
| Spoofing | Account identity | Credential theft or token replay | Strong password hashing, rotating refresh tokens, secure cookie handling |
| Tampering | Data in transit and object storage | Unauthorized edits or malicious uploads | Magic-byte validation, signed URLs, object ownership checks |
| Repudiation | Auth and access events | Missing audit trail | Audit logging for sensitive actions |
| Information disclosure | Body media, user data, token secrets | IDOR and data leakage | User-scoped queries, private object storage, encrypted body measurements |
| Denial of service | Auth endpoints and upload routes | Service abuse or brute-force attacks | Rate limiting and request-size caps |
| Elevation of privilege | Admin or authenticated actions | Cross-user access | Ownership checks and role-aware authorization |

## Threats and mitigations mapped to existing tests

| Mitigation | Threat addressed | Existing test coverage |
|---|---|---|
| Argon2id password hashing and generic auth errors | Credential theft and user enumeration | `apps/api/tests/security/test_auth.py` |
| Refresh-token rotation with family reuse detection | Token replay and session hijacking | `apps/api/tests/security/test_auth.py` |
| Per-user ownership enforcement on all user-scoped routes | IDOR and cross-user access | `apps/api/tests/security/test_auth.py` |
| Security headers, request-size limits, and strict CORS | Client-side abuse and request tampering | `apps/api/tests/security/test_auth.py` |
| Magic-byte validation, execution rejection, and oversize guardrails | Malicious or malformed upload content | `apps/api/tests/security/test_media.py` |
| EXIF stripping and sanitization of uploaded image bytes | Metadata leakage and hidden payloads | `apps/api/tests/security/test_media.py` |
| Envelope encryption for body-media storage and purge of raw media after analysis | Sensitive body-image disclosure | `apps/api/tests/security/test_media.py` and `apps/api/tests/unit/test_body.py` |
| User-scoped media retrieval checks | IDOR on media objects | `apps/api/tests/security/test_media.py` |
| Account deletion purge of related media and objects | Secondary data retention | `apps/api/tests/security/test_media.py` |
| Audit logging of auth and sensitive actions | Non-repudiation | `apps/api/tests/security/test_auth.py` |

## Additional controls

### 1. Authentication and session integrity
- Password hashing uses Argon2id with a minimum length check and a common-password deny list.
- Access tokens are short-lived and refresh tokens are stored as hashes, rotated on use, and revoked if replayed.
- Cookies are set with secure attributes and all sensitive operations require the authenticated dependency chain.

### 2. Authorization and isolation
- Every user-owned route must be scoped by `user_id` before data access.
- No object ID is accepted without verifying ownership.
- The security suite covers login, logout, refresh, media access, and profile access for different users.

### 3. Media security
- Uploaded files are validated by bytes, not by file extension.
- Image payloads are re-encoded to remove EXIF data and strip metadata.
- Body media is encrypted at rest and default behavior removes raw body images after feature extraction unless a user explicitly keeps them.

### 4. Operational resilience
- Request limits and rate limiting reduce brute-force and abuse attempts.
- Audit records allow incident analysis for account-level events and data access.
- Logs redact sensitive values such as password hashes, tokens, and IPs before they are persisted.

## Residual risks and assumptions

This model assumes the application is deployed behind a reverse proxy and with secure secret management. It also assumes the backend will continue to enforce the same authorization and validation rules at every API boundary. The automated test suite is the primary enforcement mechanism for the most critical controls, and the project should treat every new route as a security-sensitive change until it is covered by an equivalent test.
