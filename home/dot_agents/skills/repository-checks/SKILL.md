---
name: repository-checks
description: Select and interpret repository checks using Gitleaks, ShellCheck, and Git LFS. Use for staged secret scans, shell-script validation, or diagnosing LFS pointers and missing large-file content.
---

# Repository checks

Read repository instructions and existing check commands before introducing a
new validation path. Select the reference for the actual concern:

- [Gitleaks](references/gitleaks.md): directory, staged, and history scan scope;
  redaction and scanner-error handling.
- [ShellCheck](references/shellcheck.md): shell selection, diagnostics, and the
  separate Zsh syntax path.
- [Git LFS](references/git-lfs.md): pointer versus object state and scoped retrieval.

A static check is evidence for its covered contract. Do not equate a directory
secret scan with a history scan, syntax acceptance with behavioral correctness,
or a committed LFS pointer with the availability of its content.

Run the checks appropriate to the change and preserve their required scope.
Investigate tool/backend failures before reporting success. Fix the underlying
problem rather than silently disabling a check, changing the shell dialect, or
adding broad exclusions. Keep intentional exceptions narrow and documented in
the repository's existing convention.

Use read-only inspection to diagnose first. Retrieval, rewriting files, changing
tracking, and Git history migration have different effects; carry out only the
operations called for by the user's task. For remote checks and publication,
use the available GitHub workflow rather than treating a local result as proof
of the current remote PR state.
