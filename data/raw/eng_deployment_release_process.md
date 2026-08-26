---
doc_id: eng_deployment_release_process
title: Deployment & Release Process
department: Engineering
doc_type: guide
last_updated: 2025-11-10
access_role: engineering
---

## Release Cadence
Techify ships to production on a **Tuesday/Thursday release schedule**. Ad hoc releases outside this cadence require sign-off from the on-call EM and are reserved for critical fixes.

## Pipeline
All deploys run through GitHub Actions CI/CD:
1. PR merges to `main` trigger the build and test suite.
2. On success, the build auto-deploys to **staging**.
3. An engineer manually promotes the staging build to **production** via the deploy bot in #eng-deploys, typically during the Tuesday/Thursday windows.

## Feature Flags
New features are typically shipped behind a LaunchDarkly feature flag and rolled out gradually (e.g., 5% → 25% → 100% of accounts) rather than enabled for all customers immediately.

## Monitoring After Deploy
The deploying engineer is responsible for watching error rates and key dashboards in Datadog for at least 30 minutes post-deploy.

## Rollback
If error rates spike more than 2x baseline after a deploy, the on-call engineer should roll back within **15 minutes** using the one-click rollback in the deploy bot, then investigate in a follow-up incident channel.

## Freeze Periods
We observe a deploy freeze during the last week of December and during major sales events (e.g., annual user conference), except for critical security patches.

## On-Call Coordination
The on-call engineer (see On-Call Rotation Policy) is paged automatically via PagerDuty if post-deploy monitoring alerts fire, and is expected to be reachable during release windows.
