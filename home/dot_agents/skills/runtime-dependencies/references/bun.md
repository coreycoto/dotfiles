# Bun: runtime and packages

Check `packageManager`, engine constraints, Bun/mise selectors, project
`bunfig.toml`, the lockfile, and CI before selecting an install command. The
project's package manager remains authoritative even when Bun is the personal
default. A Node requirement is not automatically satisfied by Bun.

```sh
command -v bun
bun --version
mise which bun
```

Mise owns the default Bun and project versions. The global request is `1`,
following Bun 1.x with command-triggered update checks every 6 hours and a 12-hour
release delay. Exact project selectors override it and stay fixed.
Upgrade through the owner rather than running `bun upgrade` on a managed binary.
Do not create another global Bun installation to repair PATH selection.

For authorized setup in a Bun-managed project:

```sh
bun install --frozen-lockfile
# Equivalent CI-oriented entry point:
bun ci
```

A frozen install rejects a manifest/lock mismatch instead of updating the
lockfile. Installation still changes dependency files and may execute permitted
lifecycle scripts; use it in the intended checkout. Use `bun add`/`bun remove`
when a dependency change is the actual task, and review manifest and lock deltas.

Prefer the project's scripts and local CLIs to unrelated global versions.
`bunx` can acquire a package when it is absent; it is not an availability check.
Global CLI selection is declared in the dotfiles' `home/dot_config/mise/config.toml`,
with `dotfiles-tools` as the explicit preview/apply helper. Do not treat global `bunfig.toml` as a
Brewfile-like list of packages or change its settings to fix one project.

Sources: [installation](https://bun.com/docs/pm/cli/install),
[bunx](https://bun.com/docs/pm/bunx).
