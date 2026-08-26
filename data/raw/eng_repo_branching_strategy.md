---
doc_id: eng_repo_branching_strategy
title: Repository Structure & Branching Strategy
department: Engineering
doc_type: guide
last_updated: 2025-10-01
access_role: engineering
---

## Repo Structure
Techify's core product lives across three main GitHub repos: `techify-web` (frontend), `techify-api` (backend services), and `techify-infra` (Terraform/IaC). Smaller internal tools live in individually named repos under the `techify-labs` GitHub org.

## Branching Model
We use a trunk-based-ish model:
- `main` is always deployable and is protected — no direct pushes.
- Feature work happens on short-lived branches named `feat/<ticket-id>-short-desc` or `fix/<ticket-id>-short-desc`.
- Branches should be merged or closed within **5 business days** to avoid drift; stale branches older than 30 days are auto-flagged by a weekly bot.

## Merging
All merges to `main` happen via Pull Request, never direct push, enforced by branch protection rules. Squash-merge is the default merge strategy to keep history clean.

## Approvals Required
Standard PRs require **at least 1 approving review** before merge. PRs touching authentication, billing, or payment-processing code require **2 approvals**, at least one from a senior engineer on that codeowners list.

## Release Branches
For rare hotfixes to a previous release, a `release/x.y` branch may be cut from a tagged commit; this is uncommon since most deploys ship straight from `main` (see Deployment & Release Process).

## CODEOWNERS
Each repo has a `CODEOWNERS` file mapping directories to responsible teams, which GitHub uses to auto-request reviewers on PRs touching those paths.

## Commit Messages
We loosely follow Conventional Commits (`feat:`, `fix:`, `chore:`) to support auto-generated changelogs, though this isn't strictly enforced by CI today.
