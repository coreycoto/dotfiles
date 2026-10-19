# Agent tool guidance ownership

Agent Plugins owns portable development tool guidance as conditional references
inside existing workflows. Dotfiles owns personal machine setup and activation.

| Guidance | Owner and entry point |
| --- | --- |
| Search, filenames, selection and previews | Product Development: `understand-codebase` or `engineering-workflow` |
| Runtime ownership and locked dependencies | Product Development: `implement-change` or `diagnose-problem` |
| Secret scanning, shell dialects and Git LFS | Product Development: `maintain-verification` or `implement-change` |
| Browser tools, Turbo, Vercel and Neon | Product Development: `verify-product` or the relevant engineering workflow |
| GitHub connector/CLI selection and exact-candidate CI evidence | Project Management: `delivery-lifecycle` or `publish-change` |
| Personal Mise global versions, wrappers and update preferences | Dotfiles: [global-cli-tools](../home/dot_agents/skills/global-cli-tools/SKILL.md) |
| Chezmoi manifests, source/target state and activation | Dotfiles: [dotfiles-maintenance](../home/dot_agents/skills/dotfiles-maintenance/SKILL.md) |

The first five rows ship in Agent Plugins 0.10.5. Use the reviewed publisher pin
in the public plugin declaration and verify installed files and fresh-task
discovery. A marketplace declaration alone does not prove a cloud environment
loaded the plugins. Runtime and host capabilities need their own qualification.
Personal setup paths and automatic update schedules are not portable policy.

## Migration and preservation

Only the two personal skills above remain in the explicit chezmoi manifest.
The previous `developer-cli-tools`, `runtime-dependencies`, `repository-checks`
and `github-workflow` source trees are retired in favor of their plugin-owned
guidance. This source change does not delete already installed home copies.
Keep those copies until replacement installation and discovery are verified,
then review exact content and ownership before a separate, scoped retirement.
Do not activate this migration by applying all unrelated home-directory drift.

The third-party Find Skills inventory entry has been removed. That metadata
removal does not uninstall a personal skill or change its installer lock.
Vendor ui.sh and Cloudflare installations remain independently managed and are
not copied into these dotfiles or the public Agent Plugins packages.

The two personal entry points and their supporting files are declared individually
in `manifest.json` and installed under `~/.agents/skills/<name>`. Preserve other
skills and generated state. New sessions must independently verify discovery;
local installation does not establish a cloud runtime's capabilities.

Run `./scripts/check` before publication. The disposable-home gate compares actual
managed files with the manifest, exercises repeated application and preserves
an unrelated installed skill. Real-home application remains a separate action.
