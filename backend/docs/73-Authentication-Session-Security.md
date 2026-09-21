# 73 — Authentication & Session Security Architecture

## Overview
AegisAI employs enterprise-grade cryptographic authentication, stateless token signing, refresh token rotation (RTR) backed by Redis session management, and robust account-state lifecycle enforcement.

This document details the security posture, cryptographic parameters, token schemas, account enumeration defenses, and session revocation mechanics implemented in Phase 10.2.

---

## 1. Cryptographic Standards & Token Specifications

### 1.1 Signature & Algorithm Enforcement
- **Algorithm**: `HS256` (HMAC SHA-256 with 256-bit+ secret key).
- **Algorithm Allowlisting**: The JWT decoding pipeline rigorously checks the unverified header to ensure `alg == settings.ALGORITHM` and explicitly rejects `alg="none"` or unapproved algorithms.
- **Audience & Issuer Claims**:
  - `iss`: `"https://aegisai.enterprise"`
  - `aud`: `"https://api.aegisai.enterprise"`

### 1.2 Token Types & Claims Structure

#### Access Token (`type: "access"`)
- **Lifetime**: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Purpose**: Short-lived authorization token passed as HTTP Bearer token.
- **Claims Payload**:
  ```json
  {
    "iss": "https://aegisai.enterprise",
    "sub": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "aud": "https://api.aegisai.enterprise",
    "exp": 1726938000,
    "iat": 1726936200,
    "jti": "jwt_access_e8a1d7f6-...",
    "type": "access",
    "roles": ["Admin"],
    "permissions": ["chat:read", "chat:write", "mcp:configure", "user:provision"]
  }
  ```

#### Refresh Token (`type: "refresh"`)
- **Lifetime**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`).
- **Purpose**: Long-lived token used exclusively at `/api/v1/auth/refresh` to rotate token pairs.
- **Delivery**: Secure HTTP-Only, SameSite=Lax cookie (`refresh_token`).
- **Claims Payload**:
  ```json
  {
    "iss": "https://aegisai.enterprise",
    "sub": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "aud": "https://api.aegisai.enterprise",
    "exp": 1727541000,
    "iat": 1726936200,
    "jti": "jwt_refresh_92bc4a11-...",
    "type": "refresh"
  }
  ```

---

## 2. Threat Mitigations & Defenses

### 2.1 Token Type Confusion Defense
Tokens carry an explicit `type` claim (`"access"` vs `"refresh"`).
- `get_current_user` dependency verifies that `type == "access"`. Attempting to authorize API endpoints using a refresh token fails immediately with `401 Unauthorized`.
- `rotate_tokens` verifies that `type == "refresh"`. Supplying an access token to the refresh route is rejected with `TOKEN_ROTATION_FAILED`.

### 2.2 Account Enumeration Defense
The login endpoint `/api/v1/auth/login` defends against user harvesting attacks:
- Non-existent username/email and incorrect password both raise `AegisBaseException("Invalid credentials provided.", code="AUTHENTICATION_FAILED")` and return `401 Unauthorized`.
- Internal logs and DB audit trail accurately log the exact diagnostic outcome (`AUTH_LOGIN_FAILED`) along with client IP address for security operations monitoring.

### 2.3 Refresh Token Rotation (RTR) & Replay Attack Defense
1. **Single-Use Refresh Tokens**: When a refresh token is used at `/api/v1/auth/refresh`, its corresponding Redis session key (`aegis:session:{user_id}:{jti}`) is atomically invalidated, and a new token pair is issued.
2. **Replay Detection & Auto-Revocation**: If an already consumed or deleted refresh token is presented again, AegisAI identifies a potential token theft / replay attack:
   - All active session keys matching `aegis:session:{user_id}:*` are purged.
   - An audit event `AUTH_REPLAY_ATTACK_DETECTED` is recorded.
   - A `SECURITY_ALERT` exception is raised.

### 2.4 Account State & Deletion Gating
- **Suspended Accounts**: When `user.is_active == False`, logins are blocked (`ACCOUNT_SUSPENDED`), and any active bearer tokens are rejected with `403 Forbidden ("User account is suspended")`.
- **Soft-Deleted Accounts**: When `user.is_deleted == True`, credentials verification fails with `401 Unauthorized`.

### 2.5 Password Policy & Hash Boundary Enforcement
- Password validation ensures 8-128 characters, mixed character types, and rejects whitespace.
- BCrypt maximum length truncation is safely handled (72-byte safe slice) preventing hash collision attacks and DoS.

---

## 3. Authentication Audit Logging

All authentication lifecycle events are logged to the `audit_logs` database table:

| Action Code | Trigger Event |
|---|---|
| `AUTH_REGISTER` | New user account created |
| `AUTH_LOGIN_SUCCESS` | Successful user authentication |
| `AUTH_LOGIN_FAILED` | Bad password, missing user, or suspended attempt |
| `AUTH_TOKEN_ROTATED` | Refresh token rotated into new access/refresh pair |
| `AUTH_LOGOUT` | User session invalidated |
| `AUTH_REPLAY_ATTACK_DETECTED` | Replayed refresh token intercepted |

---

## 4. Verification & Testing Matrix

The dedicated test suite `backend/tests/unit/test_p10_2_auth_security.py` tests all security controls:

1. `test_password_strength_validator_rules`: Boundary conditions, minimum/maximum lengths, character complexity.
2. `test_register_user_weak_password_rejected`: Validation error gating on weak passwords.
3. `test_login_user_enumeration_defense`: Identical error messages on missing vs wrong password users, with audit log persistence.
4. `test_login_user_token_claims_and_type`: Full JWT claims validation (`sub`, `iss`, `aud`, `exp`, `iat`, `jti`, `type`, `roles`, `permissions`).
5. `test_token_type_confusion_defense`: Rejection of refresh token in Bearer authentication header.
6. `test_token_tampering_and_algorithm_none_rejected`: Rejection of corrupted signatures and `alg=none` tokens.
7. `test_refresh_token_rotation_and_replay_detection`: Normal token rotation and session family revocation upon replay attack.
8. `test_account_state_enforcement_and_audit`: Suspension (403) and deletion (401) gates.
9. `test_user_logout_and_audit`: Redis session deletion and audit log recording.
