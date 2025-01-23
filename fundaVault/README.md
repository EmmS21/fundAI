# EduVault - User & Device Management System

EduVault is a backend system for managing user authentication, device registration, and subscription tracking for FundAIHub (a store of linux native EdTech apps leveraging local AI models to helps students in Africa prepare for exams and learn new skills). 

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

## Environment Setup
```bash
# Required environment variables
export POSTGRES_SERVER="localhost"
export POSTGRES_USER="user"
export POSTGRES_PASSWORD="password"
export POSTGRES_DB="eduvault"
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
curl -X POST http://localhost:8000/api/v1/devices/register/1 \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
    "message": "Device registered successfully",
    "hardware_id": "123456789",
    "user_id": 1,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_expiry": "2024-02-23T20:00:00Z"
}
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
