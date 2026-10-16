---
name: github-workflow
description: Choose GitHub connector versus gh operations and inspect PR/check state with an explicit repository and revision. Use for GitHub CLI references, remote CI inspection, and publication handoffs alongside an existing publishing workflow.
---

# GitHub workflow reference

This skill provides tool guidance; it does not replace a publisher's installed
review or publishing workflow. Follow that workflow and repository instructions
when they apply, loading [gh operations](references/gh.md) for CLI details.

Use available connector operations for PR/issue reads and lifecycle changes.
Use `gh` for Actions checks/logs or an operation the connector cannot expose or
access; state the concrete gap before a lifecycle mutation through the fallback.
Keep ordinary branch staging, commits, and pushes in local Git rather than the
GitHub Git Data API.

Identify the repository, branch, base, and exact HEAD before publication.
Match remote checks to that revision and confirm live PR state; an older green
run does not qualify newer commits, and green checks do not mean merged.
Preserve existing user authorization through validation and necessary repairs;
do not infer permission to merge, deploy, send comments, or change unrelated
metadata from permission to inspect checks or open a PR.

Report the PR/issue URL and verified result. Prefer structured tool arguments or
body files for text, and verify uncertain write outcomes before retrying to
avoid duplicate issues or PRs. Do not modify plugin implementation/cache files
to add a personal tool reference.
