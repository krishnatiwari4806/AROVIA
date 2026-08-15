# Phase 02: Authentication & Profile Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16  
**Phase:** 02-Authentication & Profile Management  
**Areas discussed:** Token Cookie Path Scope, Registration Schema Fields, Password Reset Dev Delivery, Google OAuth Token Verification  

---

## Token Cookie Path Scope

| Option | Description | Selected |
|--------|-------------|:--------:|
| Path-scoped to `/api/v1/auth` with `SameSite=Lax` | Least privilege; the cookie is only transmitted on auth routes (/refresh and /logout), minimizing exposure across other API calls. | ✓ |
| Global path `/` with `SameSite=Lax` | Cookie is sent on all requests to the backend domain. | |

**User's choice:** Path-scoped to `/api/v1/auth` with `SameSite=Lax`.  
**Notes:** Minimizes token exposure across the network and prevents attaching cookies to unrelated API calls.

---

## Registration Schema Fields

| Option | Description | Selected |
|--------|-------------|:--------:|
| Minimal Registration + Onboarding Setup | Register with `full_name`, `email`, `password` (min 12 chars); candidate configures `target_role`, `experience_level`, and `bio` via `PUT /api/v1/auth/me` on `/onboarding` or `/profile`. | ✓ |
| Flexible Registration | Allow `target_role` and `experience_level` as optional fields in `UserRegisterRequest` if submitted upfront, while still supporting `PUT /api/v1/auth/me`. | |

**User's choice:** Minimal Registration + Onboarding Setup.  
**Notes:** Keeps initial registration frictionless and guides candidates through the dedicated `/onboarding` setup screen.

---

## Password Reset Dev Delivery

| Option | Description | Selected |
|--------|-------------|:--------:|
| Standard Console Logging in Development | Log the full clickable reset link to stdout/application logger when `ENVIRONMENT=development`; API always returns the standard generic message to prevent any response divergence. | ✓ |
| Console Logging + Dev Response Token | Log reset link to console AND return `dev_reset_token` in response body strictly when `ENVIRONMENT=development` to simplify automated API integration tests. | |

**User's choice:** Standard Console Logging in Development.  
**Notes:** Production and development API response payloads remain completely consistent, while developers can test reset links easily from the terminal logs.

---

## Google OAuth Token Verification

| Option | Description | Selected |
|--------|-------------|:--------:|
| Official Google Auth Library (`google-auth`) | Use `google.oauth2.id_token.verify_oauth2_token()` to verify signature against Google's live public certs, audience (`GOOGLE_CLIENT_ID`), issuer, and expiry. | ✓ |
| PyJWT with Cached Google JWKS | Fetch and verify Google JWKS public keys using PyJWT directly. | |

**User's choice:** Official Google Auth Library (`google-auth`).  
**Notes:** Standardized, secure verification with automated cert caching and signature verification directly supported by Google.

---

## Agent's Discretion

- Standard SlowAPI key generator using client IP address (`get_remote_address`).
- Pydantic v2 email normalization and password strength validation.
- Unit and integration testing fixtures with mock Google OAuth ID tokens.

## Deferred Ideas

- None — all topics addressed within Phase 2 boundary.
