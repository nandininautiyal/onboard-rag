---
doc_id: eng_oncall_rotation_policy
title: On-Call Rotation Policy
department: Engineering
doc_type: policy
last_updated: 2025-03-14
access_role: engineering
---

## Rotation Structure
On-call responsibility rotates weekly among backend and infra engineers, managed through PagerDuty schedules. Each engineer can expect to be on-call roughly once every 6–8 weeks depending on team size.

## Acknowledgment
When paged, the on-call engineer should acknowledge the alert in PagerDuty reasonably quickly and begin triage. We generally aim for prompt acknowledgment during business hours; overnight expectations are a bit more relaxed and are ultimately up to team lead discretion.

## Escalation
If the primary on-call doesn't acknowledge in time, PagerDuty escalates to the secondary on-call, and then to the EM. Exact escalation timing can vary by team based on the PagerDuty policy configured for that service — check your team's specific escalation policy in PagerDuty rather than assuming a company-wide number.

## Compensation
Engineers on-call during a week that includes a weekend receive on-call compensation, coordinated with Finance/Payroll; see Payroll FAQ for how this appears on your paycheck.

## Swapping Shifts
Engineers can swap on-call shifts with a teammate as needed; just update the PagerDuty schedule and give a heads-up in your team's Slack channel.

## Incident Response
Declaring a formal incident (for anything customer-impacting) follows the broader incident process documented in the internal Runbooks wiki, which is outside the scope of this policy doc.

## Tooling
On-call engineers should have PagerDuty, Datadog, and the deploy bot accessible on their phone in addition to their laptop for after-hours issues.
