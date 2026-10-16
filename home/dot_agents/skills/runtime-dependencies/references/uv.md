# uv: interpreters, environments, and locks

Read `pyproject.toml`, `uv.lock`, `.python-version`, workspace membership, and
any project uv settings before choosing the environment. These dotfiles set
`python-preference = "only-system"` and `python-downloads = "never"`; mise
owns Python installations, while uv owns dependencies and environments.

Inspect candidates without installing Python:

```sh
mise which python
uv python find --system --show-version
```

For authorized setup, explicitly select the existing interpreter and preserve
the lockfile:

```sh
uv sync --locked --python "$(mise which python)" --no-python-downloads
```

Sync creates/changes the project environment and can remove undeclared packages;
it is not a read-only check. Confirm the intended workspace, dependency groups,
and extras rather than targeting an unrelated environment. Existing environments
can retain an older interpreter until intentionally rebuilt.

`--locked` checks that requirements agree with the lockfile and refuses to
update it. `--frozen` uses the existing lockfile without checking freshness; use
it only when that distinction is intended. Ordinary `uv run` can lock and sync.
For execution in an already-prepared environment, `uv run --no-sync COMMAND`
avoids that sync; it does not prove the environment matches current requirements.

Use `uv add`, `uv remove`, and `uv lock` for an intended dependency change;
review both manifest and lockfile deltas. `uv pip` operates on an environment
rather than maintaining the project's declared dependency contract. Avoid
system/user-site installs as a repair for an isolated project.

Sources: [locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/),
[configuration precedence](https://docs.astral.sh/uv/concepts/configuration-files/).
