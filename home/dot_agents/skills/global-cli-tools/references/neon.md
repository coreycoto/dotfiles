# Neon

The old neonctl repository is archived; current development lives in neon-pkgs.
This dotfiles selection uses the npm package `neon` installed as the isolated Mise tool `npm:neon`.
The Homebrew formula is still named `neonctl`; it is deliberately excluded here.
Neon 8 declares Node >=20.19.0. Mise installation ownership does not eliminate its
runtime requirement: use the mise-managed Node already selected by the dotfiles.

```sh
neon --version
neon --help
neon projects list
```

Prefer an available Neon connector for supported operations. Specify project and
branch identifiers from inspected evidence before selecting a database. A command
may start browser authentication if not logged in; login is explicit setup.
Keep API keys and connection strings in the credential owner, never in dotfiles,
shell history, screenshots, or reports. Reading connection strings can disclose
credentials. Branch creation/deletion, resets, migrations, and SQL writes mutate
remote state; match them to the user's requested database scope.

Sources: [installation](https://neon.com/docs/cli/install),
[CLI documentation](https://neon.com/docs/cli),
[current source](https://github.com/neondatabase/neon-pkgs).
