---
doc_id: eng_code_review_guidelines
title: Code Review Guidelines
department: Engineering
doc_type: guide
last_updated: 2025-09-05
access_role: engineering
---

## Why We Review
Code review at Techify is about catching bugs early, spreading knowledge, and maintaining consistency — not gatekeeping. Reviews should be constructive and specific.

## PR Size
Aim to keep pull requests **under 400 lines of diff** where possible. Larger PRs take longer to review well and are more likely to hide bugs; consider splitting into smaller logical commits or stacked PRs.

## Review SLA
Reviewers are expected to provide a first pass within **1 business day** of being requested. If you can't get to a review in time, say so in the PR thread so the author can find another reviewer.

## Approval Requirements
Consistent with the branching strategy doc, standard PRs need at least 1 approval; PRs touching auth, billing, or payments need 2 approvals including one from the relevant CODEOWNERS group.

## What Reviewers Should Check
- Correctness and edge cases (including tests)
- Readability and naming
- Security implications, especially around user input and Confidential data handling
- Whether the PR includes adequate test coverage — new logic generally needs at least one corresponding test

## Giving Feedback
- Distinguish blocking comments ("this will break X") from nits ("consider renaming this variable").
- Prefix optional suggestions with "Nit:" so authors know they're not required to address them before merging.

## Author Responsibilities
Authors should write a clear PR description explaining the "why," not just the "what," and link the relevant ticket. Self-merging without any review is only allowed for documentation-only changes or emergency hotfixes explicitly approved by an EM.
