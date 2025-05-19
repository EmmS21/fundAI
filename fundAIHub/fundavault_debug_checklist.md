# FundaVault Debugging Checklist

This checklist helps diagnose and resolve authentication and authorization issues originating from the FundaVault service.

## Issue: `Device or user inactive, or subscription expired` (403 Forbidden)

- [ ] **1. Identify the Device ID:**
  - [ ] Note the specific `Device-ID` causing the error.
    - Device ID: `_________________________`

- [ ] **2. Check FundaVault Logs (if accessible):**
  - [ ] Review `FundaVault` service logs for more specific error details related to the Device ID.
    - Observations: `_________________________`

- [ ] **3. Verify Device Registration in FundaVault:**
  - [ ] Confirm the device was successfully registered via `POST /api/v1/devices/register` (or similar).
  - [ ] If not registered, register the device.
    - Registration status: `Registered / Not Registered / Unknown`
    - Action taken: `_________________________`

- [ ] **4. Access FundaVault Admin Capabilities:**
  - [ ] Obtain an admin token for FundaVault (e.g., via `POST /api/v1/admin/login`).
    - Admin token acquired: `Yes / No`
  - [ ] Identify FundaVault API endpoints or UI for managing device/user status and subscriptions.
    - Relevant endpoints/UI: `_________________________`

- [ ] **5. Check Device & Subscription Status in FundaVault:**
  - [ ] Using admin access, look up the current status of the identified `Device-ID`.
    - Device Status in FundaVault: `_________________________`
  - [ ] Check the associated user's subscription status (e.g., expiry date, active status).
    - Subscription Status: `_________________________`

- [ ] **6. Modify Status/Subscription in FundaVault for "Indefinite" Activation:**
  - [ ] Based on FundaVault's design:
    - [ ] Option A: Set subscription expiry to a very distant future date.
    - [ ] Option B: Apply a special "indefinite" or "never expires" flag/status.
    - [ ] Option C: Assign to a special non-expiring plan/role.
  - [ ] Implement the chosen modification using FundaVault's admin tools/APIs.
    - Action taken: `_________________________`
    - Confirmation: `_________________________`

- [ ] **7. Test FundAIHub Access:**
  - [ ] After making changes in FundaVault, retry the operation in FundAIHub that previously failed.
    - Result: `Success / Failure`
    - New error (if any): `_________________________`

- [ ] **8. Review FundaVault Code/DB (If Necessary):**
  - [ ] If the method for indefinite activation isn't clear from APIs/UI, consult the FundaVault codebase (Python/FastAPI) or its database schema.
    - Findings: `_________________________` 