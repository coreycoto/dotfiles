# GnuPG preferences and local use

These dotfiles manage no `gpg.conf` or `gpg-agent.conf` and add no GnuPG home
target. Use GnuPG's default preferences unless a specific workflow requires a
local setting. Signing identity, Git signing format and SSH agent selection
remain local choices.

Keep passphrase-cache policy, pinentry paths, keyserver settings and agent
integration local. See the
[GPG configuration reference](https://gnupg.org/documentation/manuals/gnupg/GPG-Configuration.html)
and [agent options](https://gnupg.org/documentation/manuals/gnupg/Agent-Options.html).

## Optional installation and local use

GnuPG is an optional host tool, not a requirement of the curated
Brewfile. If a workflow requires it on a new Mac, install it explicitly:

```sh
brew install gnupg pinentry
gpg --version
gpgconf --list-components
pinentry --version
```

Homebrew owns installation and updates. Its versions and prefix can differ
between Macs; no portable GnuPG version is pinned here. Resolve an installed
pinentry through `gpgconf --list-components` instead of copying a Cellar path
into shared configuration.

Terminal pinentry needs a usable interactive terminal. Supply `GPG_TTY` from
`tty` in the interactive session that needs it. If GUI signing is deliberately
chosen, review `pinentry-mac` separately and keep any `pinentry-program` path in
an unmanaged local agent configuration. Do not force GUI or loopback behavior
for all hosts. GnuPG starts its agent on demand; dotfiles do not launch or
restart it at shell startup. See [agent invocation](https://gnupg.org/documentation/manuals/gnupg/Invoking-GPG_002dAGENT.html).

Git identities, signing key selection, signing format, and signing policy stay
in the unmanaged `~/.gitconfig.local` or the owning repository's local settings.
Before activating dotfiles, preserve the currently effective settings there as
described in [local setup](setup.md#prepare-local-settings). SSH signing and
OpenPGP signing are separate choices; installing GnuPG does not authorize
switching between them.

## Disposable checks

The default configuration can be checked without reading real key material,
starting an agent, or requesting a passphrase:

```sh
(
  set -eu
  umask 077
  trial_dir=$(mktemp -d)
  printf 'Trial GnuPG home: %s\n' "$trial_dir"
  gpgconf --homedir "$trial_dir" --check-options gpg
  gpgconf --homedir "$trial_dir" --check-options gpg-agent
  printf 'GETINFO version\nGETINFO flavor\nBYE\n' | pinentry
)
```

The commands check option parsing and send informational pinentry requests.
They do not request a PIN or exercise signing or decryption. Parsing and a
protocol response do not verify a real key, passphrase prompt or GUI workflow.

The default preferences need no dotfiles activation or rollback. If a later review
selects authored preferences, back up only the affected preference files
privately, document the exact settings, and validate them in a disposable
GnuPG home first. After separately authorized live activation, exercise the
existing workflow with an already provisioned key, observe the intended
pinentry, verify the result, and repeat after restoring the previous preference
files. Reload only the relevant agent deliberately; a reload can affect active
work, and not every option takes effect without an agent restart.

Never import the whole `~/.gnupg` directory, private keys, public identity details,
revocation certificates, keyrings, trust databases, sockets, logs, or backups.
Do not generate, export, rotate, or delete keys as part of preference maintenance.
Credentials and key provisioning remain separate authorized work.
