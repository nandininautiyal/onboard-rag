---
doc_id: it_password_policy
title: Password & Authentication Policy
department: IT
doc_type: policy
last_updated: 2025-07-22
access_role: all
---

## Password Requirements
All Techify accounts (Okta SSO, email, internal tools) must use passwords that are:
- At least **12 characters** long
- A mix of upper/lowercase letters, numbers, and symbols
- Not reused across the last 10 passwords

## Rotation
Passwords must be rotated every **90 days**. Okta will prompt users automatically 7 days before expiration.

## Password Manager
All employees are provisioned a 1Password account as part of device setup. Storing shared credentials (e.g., for shared marketing or social media accounts) outside of 1Password's shared vaults is prohibited.

## Multi-Factor Authentication
MFA via Okta Verify is mandatory for all accounts, with no exceptions for convenience. SMS-based MFA is discouraged in favor of push notifications or hardware keys (YubiKey, available on request from IT).

## Shared Accounts
Shared or generic logins (e.g., a shared support@ inbox) are discouraged; where unavoidable, they must be stored in a 1Password shared vault with access logged.

## Suspected Compromise
If you suspect your password or account has been compromised, reset it immediately via Okta and notify #it-help within 1 hour. IT Security will review login activity and may force a global session logout.

## Enforcement
Repeated failure to comply with password rotation requirements after 2 reminders will result in automatic account lockout until the password is updated.
