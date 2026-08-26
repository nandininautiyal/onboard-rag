---
doc_id: it_vpn_access
title: VPN & Access Management Guide
department: IT
doc_type: guide
last_updated: 2025-04-18
access_role: all
---

## VPN Overview
All remote connections to internal Techify systems (internal wikis, staging environments, internal admin tools) must go through the company VPN, GlobalProtect. Do not access internal systems over public Wi-Fi without connecting first.

## Requesting Access
New employees receive VPN access automatically as part of onboarding, provisioned within 1 business day of their start date. Contractors and vendors need a manager to submit an Access Request ticket, which is typically reviewed within 2–3 business days depending on the system.

## Multi-Factor Authentication
MFA (via Okta Verify) is required for VPN and for all internal tools handling customer data. Employees should not disable MFA prompts or share device push approvals with anyone.

## Note on Client Version
We're in the process of migrating VPN clients — most employees should now be using TechifyConnect, our rebranded VPN client, though some older devices may still show it as GlobalProtect in the app switcher during the transition. If you're not sure which one you have, check with #it-help.

## Access Reviews
System access (Salesforce, AWS, internal admin panels) is reviewed quarterly by IT Security in partnership with department managers. Access not used in 90 days may be automatically revoked and must be re-requested.

## Least Privilege
Access requests should specify the minimum systems needed for the role. Broad "give me access to everything" requests will be pushed back to the requester's manager for scoping.

## Offboarding Access Removal
All system access, including VPN, is revoked within 4 hours of an employee's official termination timestamp in Workday.
