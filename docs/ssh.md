# SSH configuration and provisioning

The portable target is only `~/.ssh/config`. It loads the unmanaged
`~/.ssh/config.local` first, then requires confirmation for new host keys and
disables agent forwarding by default. Host aliases, account names, identities,
agent selection, and platform preferences belong in the local overlay.
Chezmoi's `private_` attributes give `.ssh` mode `700` and the managed config
mode `600`, without making the directory an exact replacement.

OpenSSH normally uses the first value obtained for each setting. Put specific
host entries before any `Host *` defaults in the overlay. The shared file resets
to `Host *` after the include so its defaults also cover unrelated hosts.
See [OpenSSH configuration](https://man.openbsd.org/ssh_config) and
[chezmoi permissions](https://www.chezmoi.io/reference/source-state-attributes/).

The shared config leaves `IdentityAgent` and `SSH_AUTH_SOCK` unchanged and
starts no agent. Retain the existing key and agent workflow until an explicit
replacement is configured and verified. Installing a password manager or using
the GitHub API does not establish SSH agent availability or authentication.

## Local overlay and onboarding

Before applying on a machine with an existing SSH config, make a private backup
of that file and any overlay, preserving permissions. Review its authored
settings locally and move the ones to retain into `config.local`; do not include
the managed config from the overlay or create an include cycle. Preserve any
existing 1Password-generated include locally. Never copy an entire `.ssh`
directory into this repository.

Use selected entries from `examples/ssh-config.example` for aliases and identity
selection. Replace placeholders privately. On a fresh machine, create the
directory and overlay only when wanted:

```sh
install -d -m 700 "$HOME/.ssh"
# Create/edit config.local privately; preserve it if already present.
chmod 600 "$HOME/.ssh/config.local"
```

Keep private keys at `600`, and review permissions on any local include files.
Shared source sets no public identity or agent socket. Before choosing an agent,
inspect the established workflow locally and keep a working connection available
through a separately authorized migration.

For a chosen 1Password workflow, use its desktop UI to create or recover an SSH
Key item, enable the SSH agent in Developer settings, and authorize the intended
client when prompted. Add only the public key to the intended service through
its reviewed UI; registration is a separate account change. Keep the private
key in 1Password. See [1Password onboarding](https://www.1password.dev/ssh/get-started).

Select 1Password for one host first by adding its documented macOS
`IdentityAgent` path to that host's local stanza. Use `IdentityFile` pointing to
a locally retained public key and `IdentitiesOnly yes` when selecting among
agent keys. Other platforms use their own supported agent integration.
Keep vault/key selection in the unmanaged 1Password agent configuration when
needed. See [gradual migration and host selection](https://www.1password.dev/ssh/agent/advanced)
and [agent configuration](https://www.1password.dev/ssh/agent).

For an existing OpenSSH/private-key workflow, retain its key and agent instead.
If creating a new file-backed key is explicitly chosen, run
`ssh-keygen -t ed25519` interactively with a new destination and a passphrase; do not overwrite
an existing key. Register its public half deliberately, keep recovery material
private, and load only the intended key into the existing agent when needed.
No key generation, registration, import, or agent change happens during apply.
See [OpenSSH key generation](https://man.openbsd.org/ssh-keygen).

## Offline validation and authorized connection checks

[`ssh -G`](https://man.openbsd.org/ssh) prints effective settings without connecting. It can still evaluate
`Match exec` commands and hostname canonicalization in arbitrary local includes.
Review those directives before using it on a live overlay. Our tests use only
synthetic includes, no agent contact, and disable hostname canonicalization.
For a reviewed alias, filter the output rather than publishing full private
host and identity settings:

```sh
ssh -G -o CanonicalizeHostname=no reviewed-alias |
  awk '$1 == "identityagent" || $1 == "identitiesonly" ||
       $1 == "stricthostkeychecking" || $1 == "forwardagent"'
```

An absent explicit `identityagent` setting retains OpenSSH's environment agent.
Parsing does not prove that a socket is available or that authentication works.
After connection authority is given, test only the intended host/client and
verify its fingerprint against an independent trusted source before accepting
a new host key. Keep host-key verification enabled; investigate changed keys
rather than disabling checks or clearing the known-host database. Agent
forwarding stays off unless a specific host workflow requires and reviews it.

Disposable-home checks exercise missing overlays, private permissions,
host-specific identity/agent selection, unrelated-host defaults, and repeated
application while retaining synthetic local keys and known hosts. Live agent
authorization and remote authentication remain manual, unverified steps.

## Rollback

Restore the backed-up SSH config and overlay with their original modes. If the
config was absent beforehand, remove only the newly managed config after
reviewing any subsequent edits and disabling that target in the source you
apply. The general backup helper retains newly created targets; it does not
delete them automatically. Retain keys, known hosts, and unrelated files.
If an agent migration was separately performed, restore the former local agent
selection and any service public-key registration deliberately; restoring this
config alone does not revoke a newly registered key or disable a password
manager. Keep keys, public identity details, sockets, known hosts, and backups
outside Git.
