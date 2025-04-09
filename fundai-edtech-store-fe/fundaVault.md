# Questions for FundaVault Team Regarding Device Registration

## API Endpoints & Authentication

1. What is the correct endpoint for admin device registration? Is there a specific endpoint like `/api/v1/admin/register-device` or similar?

2. What authentication is required for the device registration endpoint? 
   - Admin JWT token in Authorization header?
   - Any additional headers required?

## Request Format

3. What is the expected request format (JSON body) for registering a device?
   ```json
   {
     "user_id": ?,
     "hardware_id": ?,
     // What other fields are required?
   }
   ```

4. Are there specific validation rules for the `hardware_id` field?
   - Required format (UUID v4, etc.)?
   - Character/length limitations?

5. For the `user_id` field:
   - Is this a numeric ID or string?
   - How can admins retrieve a list of valid user IDs to associate with devices?

## Response Format

6. What is the expected response format for:
   - Successful registration?
   - Duplicate device registration?
   - Invalid user ID?
   - Other error cases?

## Additional User Information

7. What user details should be displayed in the admin interface to help admins correctly associate devices with users?
   - Email?
   - Username?
   - Full name?
   - Subscription status?

8. Is there a maximum number of devices that can be registered per user?

## Test Environment

9. Can you provide test user IDs we can use to verify our device registration implementation?

10. Are there any test devices already registered in the system we can reference?
