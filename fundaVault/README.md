# FundaVault - User & Device Management System

FundaVault is a backend system for managing user authentication, device registration, and subscription tracking for FundAIHub (a store of linux native EdTech apps leveraging local AI models to helps students in Africa prepare for exams and learn new skills). 

This is partof a broader platform that provides students with laptops preloaded with offline AI learning tools.

The system handles user registration, device authentication, and subscription management with offline capabilities using JWT tokens.

## Core Features
- User registration and authentication
- Device registration with hardware UUID
- Subscription management and tracking
- Offline authentication using JWT tokens
- Comprehensive status tracking and history

## Prerequisites
- Python 3.8+
- PostgreSQL/SQLite database
- Environment variables configured


## Local Development Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd fundaVault
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Environment Setup
```bash
# Required environment variables
export POSTGRES_SERVER="localhost"
export POSTGRES_USER="user"
export POSTGRES_PASSWORD="password"
export POSTGRES_DB="eduvault"

# Admin Credentials
ADMIN_EMAIL="admin@fundavault.com"
ADMIN_PASSWORD="your-secure-admin-password"
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## Admin Interface

### Admin Authentication

1. Login as admin:
```bash
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@fundavault.com",
    "password": "your-secure-admin-password"
  }'
```

2. Use the returned token for admin endpoints:
```bash
# Get all users
```bash
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer <your-admin-token>"
```
# Get system stats
```bash
curl -X GET http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer <your-admin-token>"
```

# Deactivate a user
```bash
curl -X POST http://localhost:8000/api/v1/admin/users/1/deactivate \
  -H "Authorization: Bearer <your-admin-token>"
```

## Database Schema
### User Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Subscriptions Table
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Devices Table
```sql
CREATE TABLE devices (
    hardware_id TEXT PRIMARY KEY,
    user_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_token TEXT,
    token_expiry TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## API Endpoints
### User Management

#### Register a New User
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "secure_password",
    "full_name": "John Doe",
    "address": "123 Main St",
    "city": "Lagos",
    "country": "Nigeria"
  }'
```

**Expected Response:**
```json
{
    "id": 1,
    "email": "student@example.com",
    "full_name": "John Doe",
    "address": "123 Main St",
    "city": "Lagos",
    "country": "Nigeria",
    "created_at": "2024-01-23T20:00:00Z"
}
```

### Device Management

#### Register Device
```bash
# First get an admin or user token
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "******@******.com",
    "password": "****"
  }'

# Then register a device
curl -X POST http://localhost:8000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "user_id": 1
  }'
```

**Expected Response:**
```json
{
    "user_id": 1,
    "hardware_id": "****",
    "os_type": "macos",
    "normalized_identifier": "*****",
    "is_active": true,
    "registered_at": "2025-01-25T16:23:23.942524",
    "last_verified_at": "2025-01-25T16:23:23.942524"
}
```

#### List Devices
```bash
curl -X GET http://localhost:8000/api/v1/devices/list \
  -H "Authorization: Bearer <your-token>"
```

**Expected Response:**
```json
[
    {
        "user_id": 1,
        "hardware_id": "97ae0be8-54e5-4f74-936e-9c434cd143be",
        "os_type": "macos",
        "normalized_identifier": "cdb74ce4-91cb-5774-b45d-5e8159a534a4",
        "is_active": true,
        "registered_at": "2025-01-25T16:23:23.942524",
        "last_verified_at": "2025-01-25T16:23:23.942524"
    }
]
```

### Database Schema
Update the devices table schema:
```sql
CREATE TABLE devices (
    hardware_id TEXT PRIMARY KEY,
    user_id INTEGER,
    os_type TEXT NOT NULL,
    raw_identifier TEXT NOT NULL,
    normalized_identifier TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

#### Verify Device Token
```bash
curl -X GET http://localhost:8000/api/v1/devices/123456789/verify \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Subscription Management

#### Create Subscription
```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/1
```

#### Check Subscription Status
```bash 
curl -X POST http://localhost:8000/api/v1/subscriptions/1
```

**Expected Response:**
```json
{
    "active": true,
    "end_date": "2024-02-23T20:00:00Z",
    "days_remaining": 30
}
```

## Admin Interface Testing

### 1. Admin Login
Test admin authentication by sending a POST request:

```bash
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@fundavault.com",
    "password": "your-secure-admin-password"
  }'
```

**Expected Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
}
```

### 2. Test Admin Endpoints
Using the access_token from the login response:

#### Get All Users
```bash
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Expected Response:
{
    "users": [
        {
            "id": 1,
            "email": "student@example.com",
            "full_name": "John Doe",
            "created_at": "2024-01-23T20:00:00Z"
        }
        // ... more users
    ]
}
```

#### Reset Devices Table
```bash
# First, get admin token
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@fundavault.com",
    "password": "your-secure-admin-password"
  }'

# Then reset the devices table
curl -X POST http://localhost:8000/api/v1/admin/reset-devices-table \
  -H "Authorization: Bearer <your-admin-token>"
```

**Expected Response:**
```json
{
    "message": "Devices table reset successfully"
}
```

#### Get System Stats
```bash
curl -X GET http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Expected Response:
{
    "total_users": 10,
    "total_devices": 8,
    "active_subscriptions": 5,
    "timestamp": "2024-01-23T20:00:00Z"
}
```
#### Deactivate User
```bash
curl -X POST http://localhost:8000/api/v1/admin/users/1/deactivate \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Expected Response:
{
    "message": "User 1 deactivated"
}
```

### Common Admin API Errors

#### Invalid Credentials
```json
{
    "detail": "Invalid admin credentials"
}
```

#### Missing Token
```json
{
    "detail": "Not authenticated",
    "headers": {
        "WWW-Authenticate": "Bearer"
    }
}
```

#### Invalid Token
```json
{
    "detail": "Could not validate credentials",
    "headers": {
        "WWW-Authenticate": "Bearer"
    }
}
```

## Authentication Flow
### Device Registration Process
- System generates hardware UUID using uuid.getnode()
- Verifies user has active subscription
- Creates JWT token containing:
  - Hardware ID
  - User ID
  - Expiration timestamp
  - Subscription end date
- Stores device information in database

#### Token Structure
```json
{
    "hardware_id": "unique_device_id",
    "user_id": "user_id",
    "exp": "expiration_timestamp",
    "subscription_end": "subscription_end_date"
}
```

### Error Handling
#### Common HTTP Status Codes
- 400: Bad Request (e.g., device already registered)
- 401: Unauthorized (invalid credentials)
- 404: Not Found (device/user not found)
- 500: Server Error

**Example Error Response:**
```json
{
    "detail": "Could not validate credentials",
    "headers": {
        "WWW-Authenticate": "Bearer"
    }
}
```

## Security Features
- Password hashing using bcrypt
- JWT tokens signed with HS256 algorithm
- Hardware-linked device authentication
- Subscription validation
- Token expiration and refresh mechanism

## Offline Capabilities
- JWT tokens for offline authentication
- Local subscription validation
- Token refresh when online
- Grace period for expired subscriptions

## Status Tracking
- User subscription status
- Device registration status
- Token validity
- Subscription history
