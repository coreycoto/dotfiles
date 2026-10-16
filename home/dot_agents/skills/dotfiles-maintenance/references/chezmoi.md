# chezmoi: source, preview, and target state

Use an explicit source checkout when inspecting a proposed change:

```sh
chezmoi --source /path/to/dotfiles managed --include=files
chezmoi --source /path/to/dotfiles status
chezmoi --source /path/to/dotfiles --no-pager diff
```

`diff` previews target changes; `status` reports source/target differences.
Neither proves activation. A live diff can display existing private target
contents; keep such contents out of shared logs and PRs.

Source naming encodes destination attributes: `dot_` produces a dotfile,
`.tmpl` renders a template, and other prefixes can control permissions or
execution. These dotfiles restrict managed content through `manifest.json` and
`.chezmoiroot`; update the allowlist when adding reviewed files. Avoid broad
`chezmoi add` imports of application state or generated directories.

From the reviewed checkout, follow its documented private backup procedure
before an authorized activation. Then:

```sh
chezmoi --source /path/to/dotfiles apply --interactive
chezmoi --source /path/to/dotfiles verify
```

`apply` changes the destination. `verify` compares it with the desired rendered
state. Use the same permission mask and configuration for preview/application.
Templates and run scripts can have side effects; inspect them before applying.

`chezmoi update` normally pulls the source and applies it; a plain `git pull`
only updates source. `chezmoi init --apply` also activates immediately. Do not
use either as a read-only source refresh. Updating Brewfile declarations does
not install packages unless an explicit installer is invoked.

Source: [chezmoi command overview](https://www.chezmoi.io/user-guide/command-overview/).
