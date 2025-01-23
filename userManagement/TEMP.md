Here's a detailed breakdown of the current EduVault system implementation:
Core Functionality & Data Flow:
User Management
history
Device Registration & Management
status
Subscription Management
exists
Database Schema:
Users Table:
created_at
Subscriptions Table:
created_at
Subscription History Table:
)
Devices Table:
token_expiry
Authentication & Security:
JWT Token Structure:
}
Password Security:
Passwords are hashed using bcrypt
JWT tokens signed with HS256 algorithm
Key Processes:
Device Registration Process:
details
Subscription Verification:
status
Token Refresh Process:
token
Configuration Settings:
)
Error Handling:
HTTP 400: Bad Request (e.g., device already registered)
HTTP 401: Unauthorized (invalid credentials)
HTTP 404: Not Found (device/user not found)
HTTP 500: Server Error (with detailed error messages)
Database Connections:
Uses aiosqlite for async SQLite operations
Connection pooling for efficient database access
Automatic table creation on startup
Logging:
Debug level logging enabled
Startup process logging
Database initialization logging
Endpoint access logging
This system provides:
1. Secure user registration and authentication
2. Hardware-linked device management
Subscription tracking and renewal
Offline authentication capabilities
Comprehensive status tracking
Audit trail through history tables
The system is designed to work primarily offline with periodic online synchronization for:
Token refresh
Subscription updates
Device verification
Status updates
Would you like me to elaborate on any specific component or process?