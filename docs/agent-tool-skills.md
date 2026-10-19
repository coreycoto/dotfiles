# Agent tool guidance ownership

Agent Plugins owns portable development tool guidance as conditional references
inside existing workflows. Dotfiles owns personal machine setup and activation.

| Guidance | Owner and entry point |
| --- | --- |
| Search, filenames, selection and previews | Product Development: `understand-codebase` or `engineering-workflow` |
| Runtime ownership and locked dependencies | Product Development: `implement-change` or `diagnose-problem` |
| Secret scanning, shell dialects and Git LFS | Product Development: `maintain-verification` or `implement-change` |
| Browser tools, Turbo, Vercel and Neon | Product Development: `verify-product` or the relevant engineering workflow |
| Clerk, Stripe and Cloudflare vendor skills and documentation | Product Development: the relevant engineering workflow and its provider reference |
| GitHub connector/CLI selection and exact-candidate CI evidence | Project Management: `delivery-lifecycle` or `publish-change` |
| Personal Mise global versions, wrappers and update preferences | Dotfiles: [global-cli-tools](../home/dot_agents/skills/global-cli-tools/SKILL.md) |
| Chezmoi manifests, source/target state and activation | Dotfiles: [dotfiles-maintenance](../home/dot_agents/skills/dotfiles-maintenance/SKILL.md) |

The first six rows ship in Agent Plugins 0.10.6. Use the reviewed publisher pin
in the public plugin declaration and verify installed files and fresh-task
discovery. A marketplace declaration alone does not prove a cloud environment
loaded the plugins. Runtime and host capabilities need their own qualification.
Personal setup paths and automatic update schedules are not portable policy.
Provider implementations remain independently selected and installed; the
Product Development reference routes tasks to vendor skills and official
documentation, with a documentation fallback when a specialist is unavailable.

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

## Scoped Codex cleanup

After plugin installation and fresh-session discovery are verified, compare the
four retired skill trees with their exact former tracked source before removing
them: `developer-cli-tools`, `runtime-dependencies`, `repository-checks` and
`github-workflow`. Preserve a locally edited or unrecognized tree for review.
Remove only the selected copies; a retired source entry is not authority to
delete everything under an agent skills directory.

Find Skills is a separate third-party retirement. Its user-wide source is
`~/.agents/skills/find-skills`; a client entry such as
`~/.codex/skills/find-skills` may be a symlink to it. Verify that relationship,
remove the selected client link without traversing it, and remove the selected
source tree. If `~/.agents/.skill-lock.json` contains its installer entry, remove
only `skills.find-skills`, preserving every other entry and unknown field.
Do not run a network installer to remove a local entry.

ui.sh remains under its vendor identity. Independently installed Cloudflare and
other vendor skills, the two personal managed skills, local overlays, role
configuration, active command rules, `default.rules` and hook trust are outside
this skill retirement. Do not prune old plugin caches merely because a new
version is selected: another chat may retain a hook or server path into them.
Codex history, sessions, databases and active worktrees are not disposable cache.

Record selected paths, provenance, removed versus preserved state and any
concurrent drift privately. Keep machine inventories and operational receipts
out of source. Removing skill files changes future discovery; verify it in a
new client session separately from plugin installation. Rule activation and
legacy-policy retirement remain governed by [the staged migration](codex-rules.md).
