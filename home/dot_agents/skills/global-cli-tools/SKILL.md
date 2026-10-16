---
name: global-cli-tools
description: Select and use the curated Mise global tools agent-browser, Turbo, Vercel CLI, and Neon. Use for browser automation, monorepo task selection, deployment inspection, database branch inspection, global CLI ownership, or update notices.
---

# Curated global CLI tools

Inspect the project scripts, local dependencies, installed version, and available
connectors before choosing a global fallback. Project-local binaries and their
lockfiles govern project execution. A global version is not a project upgrade.

- [agent-browser](references/agent-browser.md): browser inspection and interaction.
- [Turbo](references/turbo.md): task graph, filters, and cache evidence.
- [Vercel](references/vercel.md): deployment identity and environment selection.
- [Neon](references/neon.md): CLI migration and explicit database branch scope.

The dotfiles own the global version requests in
`~/.config/mise/config.toml`; `dotfiles-tools` previews installation and
`dotfiles-tools --update` previews global upgrades. Add `--apply` only for an
authorized installation or upgrade. Selected global CLIs check for updates every
6 hours when invoked through shims; project pins still win. Status commands read
metadata with automatic installation disabled and never launch the opted-in CLIs.

Prefer installed specialized workflow skills and available connectors when they
cover the task. These references complement them rather than replacing their
execution instructions. Commands in current upstream docs may exceed an older
pinned global version: inspect `--help` before using additional flags.
