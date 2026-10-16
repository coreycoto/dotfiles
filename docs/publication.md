# Publication and validation

`coreycoto/dotfiles` owns the portable configuration under the MIT license.
Keep machine state, private development records and private plugin
selections outside the portable source.
Keep private additions in local overlays instead of maintaining another copy
of the portable configuration.

## Review a candidate

1. Run `MISE_OFFLINE=1 ./scripts/check`. It checks the manifest, syntax,
   installation into disposable homes, shell behavior and directory secrets.
2. Review the staged paths and run the repository's Gitleaks pre-commit hook.
   Scan every available Git ref with
   `gitleaks git --log-opts=--all --redact --config .gitleaks.toml .`.
   Use a full clone; missing refs limit the scan's coverage.
3. Manually inspect source, documentation and commit metadata for personal
   paths, private email addresses, internal hostnames, private repository
   references and identifiers. Automated scanning does not establish that
   content is suitable for publication.
4. Verify the configuration without private overlays. Private catalog sources
   belong in the unmanaged `~/.config/dotfiles/agent-plugin-sources.local.json`;
   see [local plugin sources](agent-configuration.md#local-plugin-sources).
   Credentials, trust, authentication and real-home activation stay local.
5. Review the exact resulting commit before pushing. A local commit or a green
   check is not authorization to publish, change repository visibility, apply
   configuration to a live home or delete previous configuration.

If a credential enters Git, remove it from source and revoke or rotate it.
Replacing history does not undo prior credential exposure. Keep any private
development repository private when exporting reviewed source.

## Qualification boundary

The baseline is Apple Silicon macOS with Xcode Command Line Tools, Homebrew,
Mise and the prerequisites listed in the README. Ordinary checks install only
managed files in disposable homes and preserve unmanaged local settings.
They do not install every selected runtime or prove provider authentication.

A complete installation on a fresh Mac or disposable macOS VM remains
unverified. Retain that limitation until the whole documented bootstrap is
exercised there. Linux and Windows are not qualified for the macOS shell setup.
Apple Terminal profiles, themes and application preferences are outside scope;
the portable Zsh entry points and modules are included.

Publication requires separate user authorization. After an authorized push,
check hosted CI against the published commit before reporting it verified.
