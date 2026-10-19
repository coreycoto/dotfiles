# Everyday Codex use

For normal work, use the model picker, leave **Approve for me** selected and
describe the outcome you want. The baseline uses the built-in `:workspace`
permission profile with automatic approval review. You do not need a custom
permission profile or a named model profile for each task.

**Ask for approval** lets you review eligible actions yourself. **Full access**
removes the local sandbox boundary and requires an intentional task-specific
choice. Keep extra filesystem paths and network grants in local configuration.
Approvals decide when Codex pauses; the sandbox decides which resources a
command can access. Plugin installation does not grant provider or business authority.

Use the main chat's model picker. Specialist roles carry their own choices:
Luna for exploration, Sol for review and Astra for explicitly requested difficult
analysis. Their publishers own the roles and workflows.

## Setup and maintenance

After applying the reviewed dotfiles, use the same command from any repository:

```sh
dotfiles-plugins
dotfiles-plugins --apply
```

The first command previews. Apply pins native Git catalogs to the declared
commits and compares installed files with the publisher's generated packages.
Matching versions stay in place; missing or changed versions install through
native Codex using machine-local registry authentication. A private backup
precedes configuration or installation changes. Unrelated settings are preserved.
Nothing installs at shell startup or during `chezmoi apply`.

The public selection includes Communication, Product Development, Product
Management and Project Management 0.10.5. Product Development supplies six
agents; Project Management supplies five. Additional catalogs belong in the
unmanaged local source declaration described in
[local plugin sources](agent-configuration.md#local-plugin-sources).
After reviewing that file, preview and explicitly adopt its optional catalogs:

```sh
dotfiles-plugins --private
dotfiles-plugins --apply --private
```

Later updates include them while installed and enabled. Reviewing new source
commits and versions in the dotfiles declaration precedes applying an update.

When hooks or agents change, open the plugin's **Setup** in Codex, review its
hooks and accept its native agent-install form. Restart when setup asks, then
verify discovery. The updater does not grant trust or approve those forms.
If an operation fails, retain its partial receipt and inspect before retrying.

For first-machine preferences, `python3 scripts/codex-setup.py` from a reviewed
checkout previews preferences and plugins; add `--apply` after review.
The preferences include model and reasoning defaults, priority service,
feature and memory switches, and selected desktop behavior. Existing local
profiles and access definitions remain unmanaged. Backups stay local.

Memory extraction uses GPT-6 Luna; consolidation uses GPT-6.1 Sol. Their
model overrides are included in the portable preferences.

## Where changes belong

| Change | Owner |
| --- | --- |
| Personal preferences and selected plugin versions | Dotfiles |
| Reusable skills, specialist roles and workflow helpers | Their plugin |
| Repository commands, paths and operational boundaries | That repository |
| Credentials, trust, MCP connections and extra access grants | Private host state |

See the [configuration reference](agent-configuration.md) for details.
Cloud and ChatGPT Work discovery remain separately qualified.

Sources: [permissions](https://learn.chatgpt.com/docs/permissions),
[approval review](https://learn.chatgpt.com/docs/sandboxing/auto-review).
