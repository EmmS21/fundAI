# Questions for Backend Team Regarding Device Registration

## Integration Architecture

1. What is the preferred flow for device registration from the admin interface?
   - Should our Electron app call FundAIHub, which then calls FundaVault?
   - Or should our Electron app call FundaVault directly for device registration?

2. If going through FundAIHub is preferred, what is the specific endpoint we should call?
   - Is there an endpoint like `/api/admin/register-device` available?

## Request Format

3. What headers are required when calling the device registration endpoint?
   - Is the admin's JWT token required in the `Authorization` header?
   - Are any other custom headers needed?

4. What is the expected request body format?
   ```json
   {
     "user_id": ?,
     "hardware_id": ?,
     // What other fields are required?
   }
   ```

## User Management

5. Is there an endpoint to retrieve a list of users to populate the admin interface?
   - What is the URL for this endpoint?
   - What format does it return?

6. Does FundAIHub provide any endpoints to check if a device ID is already registered?

## Response Handling

7. What are the possible response codes and their meanings for device registration?
   - Success: 200? 201?
   - Failure cases: 400? 409? 500?

8. What is the response body format for:
   - Successful registration?
   - Error cases?

## Testing

9. Can you provide sample request/response pairs that we can use to test our implementation?

10. Are there any rate limits or other constraints we should be aware of when making these API calls?
