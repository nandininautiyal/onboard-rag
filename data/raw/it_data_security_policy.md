---
doc_id: it_data_security_policy
title: Data Security & Classification Policy
department: IT
doc_type: policy
last_updated: 2025-05-12
access_role: all
---

## Data Classification
Techify classifies data into three tiers:
- **Public** — marketing materials, public documentation
- **Internal** — internal wikis, roadmaps, org charts
- **Confidential** — customer data, financial records, employee PII, source code

## Handling Confidential Data
Confidential data must be encrypted both at rest (AES-256) and in transit (TLS 1.2+). It may not be copied to personal devices, personal cloud storage (Dropbox, personal Google Drive), or USB drives.

## Access Principle
Access to Confidential data follows the principle of least privilege and is granted based on role, reviewed quarterly alongside the process described in the VPN & Access Management guide.

## Customer Data
Customer data lives in our production AWS environment and designated Salesforce fields. Engineers accessing production customer data for debugging must use the audited "break-glass" process and log the reason in the #eng-breakglass channel.

## Incident Reporting
Any suspected data security incident (leaked credentials, phishing click, lost device with Confidential data, suspicious account activity) must be reported to IT Security within **24 hours** of discovery via security@techify.io or #it-security-urgent.

## Third-Party Tools
New SaaS tools that will store or process Confidential data require a security review before purchase, coordinated with IT Security and Finance (see Procurement section of the Travel & Accommodation policy's related Finance docs).

## Annual Training
All employees complete an annual data security training module in Lessonly, and Engineering additionally completes a secure coding refresher tied to the code review process.
