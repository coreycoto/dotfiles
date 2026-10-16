---
name: runtime-dependencies
description: Resolve runtime selection and dependency workflows with mise, uv, and Bun. Use for interpreter/version conflicts, project setup, locked installs, or deciding which manager owns a runtime, environment, or CLI.
---

# Runtime and dependency management

Identify the project directory, declared versions, lockfile, and actual executable
before changing an installation. Read project instructions and CI selectors;
compatibility ranges and minimum-supported versions are not exact local pins.

| Responsibility | Owner in these dotfiles |
|---|---|
| Node, Python, Rust versions | mise; Rust uses rustup underneath |
| Python packages and project virtual environments | uv |
| Default Bun binary | Mise, following Bun 1.x with update checks every 6 hours |
| Other project Bun versions | mise |
| JavaScript project packages | The project's declared package manager |
| Curated global JavaScript CLIs | Mise, from the global tool declaration |

The installed dotfiles uv policy uses existing system/PATH interpreters and
prevents Python downloads. A mise-selected interpreter counts as a system
interpreter to uv. Project settings can override the user policy. Diagnose that
precedence before adding a second installation or changing global defaults.

Load only the relevant reference:

- [mise](references/mise.md): resolution, selectors, Rust ownership, and explicit installation.
- [uv](references/uv.md): interpreter selection, environments, and lockfile semantics.
- [Bun](references/bun.md): runtime ownership, frozen installs, and local/global CLIs.

Use the existing selectors and lockfiles for ordinary setup. Change dependency
requirements, lockfiles, or runtime versions when the task calls for it, and
validate those changes through the owning project's checks. If a required version
is missing, report that fact and install it explicitly within the authorized
setup scope; do not silently substitute another version or enable auto-install.

Verify resolution from the project directory after a change. A version command
proves executable selection, not application compatibility. Run the relevant
project checks without broadening a dependency fix into a machine-wide upgrade.
