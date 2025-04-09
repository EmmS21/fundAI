## Requirements & Questions for User Subscription Activation

**Feature:** Admins need to activate 1-month subscriptions for users via the client app.

**Interaction:** The client app will likely call a FundAIHub endpoint, which in turn needs to interact with FundaVault to manage subscription status.

**Questions for FundaVault Team:**

1.  **Subscription Endpoint:** What specific FundaVault API endpoint should the *backend* (FundAIHub) call to create or update a user's subscription record?
2.  **Required Data:** What data does this endpoint require?
    *   User identifier (`user_id`? `email`?)
    *   Subscription start date (or does FundaVault set this automatically?)
    *   Subscription end date (or duration, e.g., "+1 month")?
    *   Any other necessary fields?
3.  **Authentication:** What authentication does this endpoint require (presumably an internal service token or the Admin JWT passed through from FundAIHub)?
4.  **Subscription Representation:** How is the subscription status/expiry date stored and represented in the user's JWT payload after activation? (This affects how the FundAIHub middleware might validate access).
5.  **Idempotency:** Is the subscription activation endpoint idempotent (safe to call multiple times)? What happens if an already active subscription is activated again?
