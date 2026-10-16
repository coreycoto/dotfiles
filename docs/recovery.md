# Recovery

Keep an existing terminal open while changing shell configuration. Backups can
contain credentials and private settings; retain them outside Git and restrict
access. Use the exact backup selected during [setup](setup.md#back-up-and-preview).

## Restore managed files

From the reviewed checkout:

Review edits made since the backup before restoring. Restoring a recorded file
replaces its current contents with the saved copy.

```sh
python3 scripts/backup.py restore \
  --home "$HOME" \
  --backup /path/to/the/selected/backup
```

The helper validates the receipt and checksums before restoring recorded files
and symlinks with their original modes. It rejects targets outside the manifest
and its explicit local-target list. It leaves targets that were absent before
the backup in place, preserving files subsequently created at those paths.
Review any retained targets individually, especially shell entry points; disable the source
target before separately choosing to remove a newly created file.

Restore separately saved overlays, such as SSH `config.local` or the private
plugin source declaration, from their selected private copies. Review intervening
edits and preserve their restrictive permissions. These extra copies are outside
the general backup helper's receipt.

## Verify the restored setup

Open another shell and check command resolution, Git identity/signing, project
PATH entry and exit, and any workflow affected by the change. Keep the first
terminal available until those checks pass. A restored file is not proof of
working authentication or a correct provider connection.

Restoring dotfiles does not reinstall packages or change runtime versions.
Use the intended package manager and reviewed versions for package recovery,
then regenerate Mise shims and verify real executable paths. Preserve existing
installations until their dependents and replacement workflows are checked.
Inspect an existing Homebrew package and its dependents before changing it;
do not infer that a package is disposable from PATH precedence or age.

Follow the relevant guide for application-specific state and receipts:

- [Mise and runtime selection](mise.md#verification-and-recovery)
- [Oh My Zsh](oh-my-zsh.md#rollback-and-validation)
- [SSH](ssh.md#rollback)
- [VS Code](vscode.md#updates-and-rollback)
- [Codex preferences and plugins](agent-configuration.md)

Preserve unrelated caches, credentials, keys, sessions, local configuration and
project selectors throughout recovery. Cleanup and deletion require their own
reviewed scope.
