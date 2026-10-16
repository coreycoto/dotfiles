# Agent tool skills

The dotfiles own six small skills, grouped by the decision an agent needs to
make. They cover runtime and CLI ownership and focused workflows for selected tools. Each
entry point loads only the references relevant to the current task.

| Skill | Tool references | Decision it supports |
|---|---|---|
| [developer-cli-tools](../home/dot_agents/skills/developer-cli-tools/SKILL.md) | ripgrep, fd, fzf, zoxide, bat | Contents versus filenames, interactive versus unattended selection, stable previews |
| [runtime-dependencies](../home/dot_agents/skills/runtime-dependencies/SKILL.md) | mise, uv, Bun | Runtime ownership, project selectors, interpreter resolution, locked installs |
| [dotfiles-maintenance](../home/dot_agents/skills/dotfiles-maintenance/SKILL.md) | chezmoi | Source versus target state, explicit manifests, preview and activation |
| [repository-checks](../home/dot_agents/skills/repository-checks/SKILL.md) | Gitleaks, ShellCheck, Git LFS | Scan boundaries, shell dialects, pointers versus available object content |
| [github-workflow](../home/dot_agents/skills/github-workflow/SKILL.md) | gh and connector selection | Exact PR/check evidence and CLI fallback alongside the installed publishing workflow |

| [global-cli-tools](../home/dot_agents/skills/global-cli-tools/SKILL.md) | agent-browser, Turbo, Vercel CLI, Neon | Global fallback selection, browser and remote operation scope |

## Distribution and discovery

All authored entry points, references, and UI metadata are declared individually
in `manifest.json`. Reviewed chezmoi application installs them under
`~/.agents/skills/<name>`; no third-party skill tree or plugin implementation is
copied into this repository. Existing unrelated skills stay unmanaged.

Use the normal private backup, preview, apply, and verify process described in
the README. After application, start a new Codex session and verify the six
names appear in the skill list. They allow automatic selection and can also be
invoked explicitly, for example `$runtime-dependencies`. Another client needs
to support the user skill location or receive the entry-point path explicitly.
Local installation does not establish discovery in a cloud environment.

The GitHub skill is a reference layer, not a second publication engine. It
routes lifecycle operations to available connectors and the existing installed
publishing workflow; it uses gh for Actions evidence and concrete connector
gaps. Publisher-owned workflow skills and caches remain in their own packages.

## Maintenance

Add detail when a recurring decision or failure demonstrates its value. Keep
installation ownership and project policy distinct from generic tool commands;
use the project manifest, lockfile, and CI as the authority for that project.
References link to upstream documentation rather than copying command manuals.

Run `./scripts/check` before publication. Its disposable-home checks compare
actual chezmoi targets with the manifest, exercise repeated application, and
preserve an unrelated installed skill. Separately validate skill frontmatter,
UI prompts, and relative reference links in both source and a disposable install.
Software installation and real-home activation remain explicit operations.
