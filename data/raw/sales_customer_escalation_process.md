---
doc_id: sales_customer_escalation_process
title: Customer Escalation Process
department: Sales
doc_type: policy
last_updated: 2025-06-25
access_role: sales
---

## Severity Levels
Customer issues are triaged into three severities:
- **Sev 1 (Critical)** — production outage or major data issue affecting a customer's core workflow
- **Sev 2 (High)** — significant bug or degraded functionality, workaround may exist
- **Sev 3 (Normal)** — minor bugs, feature requests, general questions

## Escalation SLA
Customer Success Managers (CSMs) must escalate any Sev 1 issue to the **CSM Lead within 2 business hours** of the customer report. Sev 2 issues should be escalated within 1 business day if unresolved.

## Executive Notification
Sev 1 issues affecting a top-20 account (by ARR) trigger an automatic notification to the VP of Customer Success and the account's Account Executive, in addition to the CSM Lead.

## Engineering Involvement
If a Sev 1 is confirmed to be a product bug (not user error or config issue), the CSM Lead loops in the on-call engineer via the #eng-escalations Slack channel, referencing the On-Call Rotation Policy for who's currently on-call.

## Communication Cadence
For open Sev 1 issues, the assigned CSM must send the customer a status update at least every 2 hours until resolution or a clear ETA is established.

## Post-Incident
After any Sev 1, the CSM completes a brief internal write-up within 3 business days, and Engineering completes a postmortem per the incident process referenced in the On-Call Rotation Policy.

## Escalation Outside Business Hours
After-hours Sev 1 issues from Enterprise-tier customers can trigger the PagerDuty on-call rotation directly via the emergency support line, bypassing the standard CSM-first flow.
