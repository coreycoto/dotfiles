# Working on these dotfiles

- Keep the managed targets in `manifest.json` explicit and limited. Read
  `docs/inventory.md` before adding a new application or file.
- Treat the repository as publishable source even while it is private. Never
  import credentials, private keys, histories, sessions, backups, caches,
  installed dependencies, or whole application directories.
- Use local overlays for identity, signing settings, credentials, and private
  configuration. Do not capture live secrets in test fixtures or tool output.
- Run `./scripts/check` before committing. It validates the manifest, syntax,
  installation in a disposable home, PATH behavior, and secret detection.
- Stage named paths and use the repository's Gitleaks pre-commit hook. Run the
  staged scan before publication, and scan all Git refs before public export.
- Applying to the user's real home, merging, deleting old configuration, and
  creating or publishing the public repository are separate steps. Carry out
  only the steps the user has authorized in the current conversation.
- Keep shell startup quiet and offline by default. The machine-local opt-in
  status banner reads cached data and refreshes asynchronously with a shared
  lock and cache lifetime. Never install or upgrade software at startup or
  through automatic chezmoi scripts.
