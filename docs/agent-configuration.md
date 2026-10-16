# Portable agent configuration

For normal use, start with [the short Codex guide](codex.md).
`python3 scripts/codex-setup.py` previews preferences and the selected plugins;
`--apply` performs the setup. The individual helpers remain available for diagnosis.

Dotfiles own personal preferences and installation declarations. Publishers own
plugin implementations. Each project keeps its product instructions, permissions
and dependency contract. Installation does not establish authentication, hook
trust, agent selection or cloud discovery.

## Managed files and local state

The manifest manages `~/.codex/AGENTS.md`, `~/.codex/autonomy-policy.md`,
`~/.codex/preferences.toml`, the personal marketplace template and the plugin
selection declaration. The main `~/.codex/config.toml` stays local because it
also holds project trust, plugin registrations, app permissions and MCP connections.
Credentials, sessions, databases, memories, logs, caches, notification scripts and
host-specific paths stay outside source control.

The preferences template declares 30 leaf keys: model and reasoning defaults,
personality, priority service, the built-in `:workspace` permission selection,
`on-request` approvals with automatic review, selected feature and memory
switches, memory model overrides, desktop behavior and the additive reviewer hint. It contains no
custom permission definitions or concrete filesystem/network grants.

Per-chat memory extraction uses `gpt-6-luna`; global consolidation uses
`gpt-6.1-sol`. These are the supported `memories.extract_model` and
`memories.consolidation_model` overrides. Memory files remain outside source control.
See [memory configuration](https://learn.chatgpt.com/docs/customization/memories#configure-local-memories).

Preview and explicitly merge the declared leaves through native Codex:

```sh
python3 scripts/codex-preferences.py
python3 scripts/codex-preferences.py --apply
```

Application requires chezmoi and Codex 0.162.0 or later. The helper uses the
observed configuration version, creates a private backup before edits and
verifies preservation of every other key, including nested desktop host state,
MCP connections and any `auto_review.policy`. Unknown input keys and alternate
access selections are rejected. The helper never prints the live configuration
or reloads active chats. The preferences file is input to this merge, not a
CLI `--profile` preset.

Both helpers resolve an installed Mise-owned Codex binary offline before any
isolated-home version check. A missing CLI requires explicit installation.

Use the main chat's model picker rather than task-specific model profiles.
Specialist model routing stays in the plugins. Normal access uses **Approve for
me** with the built-in workspace profile; custom profiles are unnecessary for
this baseline. Existing local profiles and permission definitions stay
unmanaged; routine preference application does not delete them.

## Shared autonomy guidance

Edit [the policy source](../home/dot_codex/autonomy-policy.md) to change the
canonical autonomy guidance. Chezmoi includes its literal contents in global
`AGENTS.md`; quotes, Unicode, backslashes and literal template syntax remain
intact. The installed Markdown copy is also available for human review.

Codex 0.160.0's [synchronous reviewer setup](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/core/src/guardian/review_session_setup.rs#L111-L117)
passes the parent's applied global and thread instructions to the review session.
Keep the core policy in that global guidance rather than duplicating it in
`auto_review.extra_policy`. A nonempty `AGENTS.override.md` takes precedence over
`AGENTS.md`; existing overrides remain local and must be reviewed separately.

The supplement is a short context hint: follow the parent's applied guidance and,
when relevant context is missing, use permitted read-only checks to consult the
first nonempty `AGENTS.override.md` or `AGENTS.md` in the active `$CODEX_HOME`,
defaulting to `~/.codex`. Chezmoi serializes that hint as TOML. It is not a
file-include directive and does not establish shared memory or guarantee a read.

[Codex #50309](https://github.com/openai/codex/issues/50309) documents a 0.160.0
synchronous reviewer catalog template that omits the extra-policy placeholder.
Storing the hint in TOML does not establish delivery to the reviewer.
The core policy uses the inherited global-guidance path; the hint remains
advisory and may be omitted by an affected template.

The policy preserves authorized scope across checks, repairs, routine revisions
and turns, while retaining exact-candidate promotion restrictions and separate
authorization for actions outside that scope. It does not select an approval
mode, expand sandbox or credential access, or override forbidden Rules and
higher-priority policy.
Managed `guardian_extra_policy` takes precedence over this local supplement.

Applying chezmoi renders the instructions and preferences but does not merge
the main Codex configuration. After reviewing the rendered diff, run the explicit
preference helper above to activate the declared keys, then restart Codex before
relying on them in new tasks. No apply or installation runs at shell startup.

Disposable-home checks compare the manifest with the actual chezmoi targets and
allow only the three reviewed `.codex` files. Repeated application preserves
machine configuration, credentials, sessions, installed dependencies, memories,
Rules and a local global-instruction override. A changed policy source updates
global instructions and the installed Markdown copy without expanding the hint.
Native configuration checks establish persistence and preservation of other
keys. When the native client is available, offline prompt inspection verifies
the main agent's global instruction discovery in default and custom Codex homes,
nonempty override precedence and empty-override fallback. These checks make no
model request; they do not verify reviewer prompt delivery or approval behavior.

## Purpose-specific agents

Each publisher owns its roles, model choices and native Setup workflow.
Product Development 0.10.2 supplies six agents and Project Management 0.10.2
supplies five. Other catalogs and their selections belong in local configuration.
Luna handles exploration, Sol handles demanding review and Astra is reserved
for explicitly requested difficult architecture analysis. A parent model
profile is unnecessary for this routing.

Use each plugin's native Setup for changed hooks or agents. Restart when setup
requests it and verify role discovery separately. Installation does not prove
that an active chat reloaded its configuration or selected a role.

## Personal plugins

`~/.config/dotfiles/agent-plugins.json` uses version 3 of the declaration:
exact Git commits and plugin versions, installed through native Git catalogs.
Each catalog uses the declared `.agents/plugins` sparse checkout; source
verification independently reads the full pinned publisher tree.
The public selection includes Communication, Product Development, Product
Management and Project Management 0.10.2 at
`6523011c94f94afb716d51efcf4ed5be09a3e203`.

```sh
dotfiles-plugins
dotfiles-plugins --apply
```

The updater previews by default. Apply verifies clean source at each declared
commit, generates the publisher's Codex projection in temporary local storage
and compares installed package bytes with that projection. Matching installed
versions remain in place. Only missing or changed versions are installed.
Native catalog pins are written with configuration version checking and a
private backup. Unrelated plugins, trust, permissions and host state are preserved.
Unknown same-name catalog sources and explicitly disabled selections stop for
review rather than being replaced or enabled.

Registry authentication stays machine-local; an installation that needs it
uses the existing native configuration. No package publication is performed.
Source checkouts, generated verification packages, native caches and backups
stay outside Git. Nothing installs at shell startup or during `chezmoi apply`.
The repository wrapper and installed launcher share one implementation.

Compatibility handling for a version-2 declaration requires that explicit
input. The version-3 setup preserves other local bundles and ownership records.

### Local plugin sources

Keep additional catalog URLs, commit pins and plugin selections in the unmanaged
`~/.config/dotfiles/agent-plugin-sources.local.json`. Start from
[`examples/agent-plugin-sources.example.json`](../examples/agent-plugin-sources.example.json),
replace its example repository, zero commit and plugin selection with reviewed
values, and restrict the file to mode `600`. Do not put credentials in this file.
Authentication remains in the native client or credential manager.

The updater appends these catalog entries to the public version-3 declaration
before validation. Local names must be distinct from public names, sources must
use credential-free HTTPS URLs and immutable commits, and every local source
must set `optional` to `true`. Unknown fields or collisions stop before native
commands or installation. An absent local file leaves the public selection
unchanged. `--local-manifest PATH` selects another local file explicitly.
An explicitly selected file must exist.

The first adoption of local catalogs remains explicit:

```sh
dotfiles-plugins --apply --private
```

Preview with `dotfiles-plugins --private` before applying. Subsequent updates
include a local selection while it remains installed and enabled. Chezmoi does
not manage or replace the source overlay. Public catalog updates continue to
come from dotfiles without duplicating their pins in the local file.

### Local marketplace entries

The personal home marketplace retains its `codex-home-local-marketplace`
identity. Its optional entries come from the unmanaged mode-600 file
`~/.config/dotfiles/agent-plugins.local.json`; see
`examples/agent-plugins.example.json`. Relative paths are resolved from the
user home, not from the JSON's directory. Do not put credentials in this file.
This file supplies entries to the personal marketplace; it is separate from
the local Git catalog source declaration above.
A product's local marketplace registration should point at its durable
checkout or package catalog, rather than a temporary review directory. These
host-specific registration paths remain outside the portable declaration.

Every native mutation is attempted once. A failure retains completed and
failed actions; inspect that partial receipt before retrying. The updater
never grants hook trust, approves an agent-install form or reloads a chat.

## Third-party skills

`tools/skills.json` records the existing standalone skill groups without copying
their contents. The global Vercel installer lock identifies the Find Skills
source and a folder hash, but does not establish its source commit. The UI and
Cloudflare installations have no reviewed source pins in that lock.

Keep the existing installations. To reproduce them later, qualify an exact
provider source revision and selected skill paths, then use the provider's
installer or Codex skill installer at that revision and verify the installed
content. Do not treat a folder hash as a commit SHA or install from a guessed
source. Publisher-owned optional `skills-lock.json` files are separate contracts
for dependencies selected by a consumer; installing a plugin does not restore
them. Optional dependency installation remains a separate action.

## Cloud environments

Local installation does not establish Codex Cloud or ChatGPT Work discovery.
Select the repository and exact reviewed revision in a fresh environment to
qualify plugin acquisition and discovery separately. Prepare Python, Git and a
compatible Codex CLI, then run:

```sh
python3 scripts/agent-plugins.py --apply
```

Record the source revision, installed package versions, enablement and actual
skills visible in a fresh task. The repository's own `dotfiles-maintenance`
skill should be discovered from `.agents/skills/`; shared plugin implementations
must come from the pinned publisher. Confirm no dependency on Mac-only paths,
credentials or caches. Treat missing Git access or client discovery as a failed
or unverified gate. Keep this cloud setup limited to plugins; do not apply the
macOS shell configuration to the container.

Cloud and ChatGPT Work require their own installation and discovery checks.
Verify each client independently before relying on its discovery behavior.

Sources: [personal marketplaces](https://developers.openai.com/plugins/build/plugins#marketplace-metadata),
[native configuration API](https://learn.chatgpt.com/docs/app-server),
[reviewer configuration](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml),
[automatic review](https://learn.chatgpt.com/docs/sandboxing/auto-review),
[global instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md#create-global-guidance),
[literal file inclusion](https://www.chezmoi.io/reference/templates/functions/include/),
[TOML serialization](https://www.chezmoi.io/reference/templates/functions/toToml/),
[model selection](https://learn.chatgpt.com/docs/models#choosing-a-model),
[subagent models](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents),
[cloud skill availability](https://learn.chatgpt.com/docs/environments/cloud-environments#current-limitations),
[skill distribution](https://learn.chatgpt.com/docs/enterprise/skills#skill-distribution-and-administration).
