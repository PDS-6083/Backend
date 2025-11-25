# AeroSync Backend

Backend API for AeroSync built with Python FastAPI.

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Next.js

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the environment variables file:
   ```bash
   cp .env.example .env
   ```
4. Update `.env` with your configuration values

### Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Health Check: `http://localhost:8000/health`

### Authentication

#### Login

**Endpoint:** `POST /api/login`

**Description:** Authenticates a user and sets an authentication cookie.

**Request Body:**
```json
{
  "user_type": "admin",
  "email": "user@example.com",
  "password": "password123"
}
```

**User Types:**
- `admin`
- `pilot`
- `cabin crew`
- `scheduler`
- `engineer`

**Success Response (200 OK):**
- Sets an HTTP-only cookie named `auth_token`
- Response body:
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "user_type": "admin"
  }
}
```

**Failure Examples:**

1. **Invalid Credentials (401 Unauthorized):**
```json
{
  "success": false,
  "message": "Invalid email or password",
  "error": "AUTHENTICATION_FAILED"
}
```

2. **Invalid User Type (400 Bad Request):**
```json
{
  "success": false,
  "message": "Invalid user type. Must be one of: admin, pilot, cabin crew, scheduler, engineer",
  "error": "INVALID_USER_TYPE"
}
```

#### JWT Token Specifications

**Token Format:** JSON Web Token (JWT)

**Algorithm:** HS256 (HMAC with SHA-256)

**Token Structure:**
The JWT token consists of three parts: `header.payload.signature`

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload (Claims):**
```json
{
  "sub": "user@example.com",
  "user_id": 1,
  "user_type": "admin",
  "iat": 1234567890,
  "exp": 1234571490
}
```

**Claims Description:**
- `sub` (Subject): User's email address
- `user_id`: Unique user identifier
- `user_type`: User role (admin, pilot, cabin crew, scheduler, engineer)
- `iat` (Issued At): Unix timestamp when the token was issued
- `exp` (Expiration): Unix timestamp when the token expires

**Token Expiration:**
- Default expiration: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`)

**Cookie Details:**
- **Name:** `auth_token`
- **HTTP-Only:** Yes (prevents JavaScript access)
- **Secure:** Configurable (set to `True` in production)
- **SameSite:** Lax (CSRF protection)
- **Path:** `/`

**Usage:**
The JWT token is automatically sent by the browser in subsequent API requests via the `auth_token` cookie. Include the cookie in requests to protected endpoints:

```bash
curl -X GET http://localhost:8000/api/protected-endpoint \
  -H "Cookie: auth_token=<jwt_token>"
```

**Token Validation:**
Protected endpoints will validate the JWT token by:
1. Verifying the signature using the `SECRET_KEY`
2. Checking token expiration (`exp` claim)
3. Validating the token structure and required claims

