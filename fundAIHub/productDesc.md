We need help understanding why FundaVault might be indicating that these tokens are invalid during the validation check performed by the FundAIHubStore backend.

**Questions:**

1.  **Token Validation Endpoint & Mechanism:**
    *   What specific API endpoint on FundaVault (`fundai.onrender.com`) should our FundAIHubStore backend call to validate a Bearer token it receives?
    *   What HTTP method (GET, POST, etc.) does this endpoint expect?
    *   What parameters, headers, or request body does the validation endpoint require (e.g., does it expect the token itself in the body or a header)?

2.  **Validation Logic:**
    *   What specific checks does FundaVault perform when validating a token via this endpoint? (e.g., Signature verification, expiration check (`exp` claim), "not before" check (`nbf` claim), issuer check (`iss` claim), audience check (`aud` claim), user existence, checking against a revocation list?).

3.  **Signing Keys:**
    *   How are the JWTs signed (e.g., symmetric HS256, asymmetric RS256)?
    *   If asymmetric, does FundaVault expose a public key endpoint (e.g., JWKS URI) that consuming services like FundAIHubStore could *optionally* use for preliminary signature verification? (Or does validation *always* require calling the FundaVault validation endpoint?)

4.  **Token Claims:**
    *   What are the standard claims included in the JWT payload issued upon successful login? (e.g., `sub`, `iss`, `aud`, `exp`, `iat`, `nbf`, user ID, roles, etc.)?

5.  **Error Responses from Validation Endpoint:**
    *   When FundaVault's validation endpoint determines a token is *invalid* (expired, bad signature, revoked, etc.), what specific HTTP status code and response body does it return to the caller (FundAIHubStore)? Understanding this helps ensure our middleware correctly interprets the response.

6.  **Logging:**
    *   Does FundaVault log token validation attempts made via its validation endpoint?
    *   Can you check FundaVault logs (around the time we see the 401s) for incoming validation requests from FundAIHubStore?
    *   If validation failures are logged, what is the specific reason recorded (e.g., "token expired", "signature invalid", "user not found")?

7.  **Token Lifetime:**
    *   What is the configured expiration time (lifetime) for JWTs issued by FundaVault?

8.  **Environment Consistency:**
    *   Are there separate staging/production environments for FundaVault? Can we confirm that our FundAIHubStore backend (`fundaihubstore.onrender.com`) is configured with the correct URL for the corresponding FundaVault environment (`fundai.onrender.com`)?

9.  **Token Revocation:**
    *   Does FundaVault support token revocation (e.g., upon logout or password change)? If so, how does this affect validation?

10. **Clock Skew:**
    *   Is there any potential for significant clock skew between the FundaVault server and the FundAIHubStore server that might affect time-based claim validation (`exp`, `nbf`, `iat`)?

Understanding these points will help us pinpoint whether the issue lies in the token itself, the validation process on FundaVault, or the communication/configuration between FundAIHubStore and FundaVault.
