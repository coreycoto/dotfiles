# Gitleaks: choose the scan boundary

Use the repository's existing config and pre-commit hook when present. Typical
commands from the checkout are:

```sh
gitleaks dir --redact --no-banner --config .gitleaks.toml .
gitleaks git --pre-commit --staged --redact --no-banner --config .gitleaks.toml .
gitleaks git --log-opts=--all --redact --no-banner --config .gitleaks.toml .
```

Omit `--config` if that repository has no such configuration. Directory scans
cover present files, staged scans cover proposed commits, and Git scans cover
the selected locally available history. A shallow clone or missing refs limits
history coverage; `--all` cannot scan refs that were never fetched.

Keep redaction enabled when reporting findings. Report the rule, file/location,
and remediation without copying a credential into a new artifact or comment.
Removing a secret from the current file does not revoke it or remove past copies;
coordinate rotation and history work within the authorized scope.

A nonzero result may be a finding or an execution failure; inspect diagnostics.
These dotfiles' hook also rejects error diagnostics even if the scanner returns
zero. Repair the Git/scanner environment and repeat the intended scan instead
of bypassing the hook or treating an incomplete scan as clean.

Use narrow repository-reviewed allowlists only for verified false positives,
not broad ignores that hide real findings. A scan's success does not establish
that a value never left the machine.

Source: [Gitleaks CLI](https://github.com/gitleaks/gitleaks).
