# Portless development setup

Portless belongs to each maintained monorepo's development dependencies. The
project package manager installs it, and the project manifest and lockfile select
its version. Use the installed project binary or the project's reviewed scripts.
There is no Homebrew or Bun-global Portless selection in these dotfiles.

This assessment selects documentation only: no portable user preferences are
needed. The reviewed local state entries were generated routes, logs,
certificates, and trust/process markers. Application names, launch commands,
ports, allowed development origins,
proxy rewrites, HTTPS requirements, and any `portless.json` or `package.json`
`portless` configuration belong in the owning project. Machine-specific choices
can be supplied explicitly for a session. Dotfiles do not export `PORTLESS_*`,
install a service, or start a proxy during shell startup or chezmoi application.

The commands below were checked against Portless 0.13.1, the version resolved by
an existing maintained monorepo. This is an evaluated version, not a new pin for
every project. Read the installed version's help before changing its setup.
See the [versioned upstream guide](https://github.com/vercel-labs/portless/blob/551434f0e2a688c1c7eccfead411eb2cdd3109c9/README.md)
and [package requirements](https://github.com/vercel-labs/portless/blob/551434f0e2a688c1c7eccfead411eb2cdd3109c9/packages/portless/package.json).

## Install and update explicitly

Read the project's runtime selectors, package manager, dependency version, and
development instructions first. Portless 0.13.1 requires Node.js 24 or later;
select an installed mise runtime as described in [tool ownership](tool-ownership.md).
From a Bun-owned project, for example:

```sh
cd /path/to/monorepo
node --version
bun install --frozen-lockfile
./node_modules/.bin/portless --version
./node_modules/.bin/portless --help
```

Use the equivalent locked installation for another project package manager.
If Portless is missing, add a reviewed development dependency in that project
and commit its manifest and lockfile together. A global install, `bunx`, or
`npx` must not silently supply a different version. Updates use the project's
normal dependency review, followed by its development smoke checks. Reinstall
from the prior reviewed manifest and lockfile to roll back a package update.
Removing a package does not stop an existing proxy or remove CA trust.

## Localhost and normal development

Portless 0.13.1 defaults to HTTPS on port 443, generates local certificates, and
attempts to trust its CA. Running an application can auto-start that proxy.
Its default also synchronizes route names into `/etc/hosts`. Review these
effects before the first development run; dependency installation alone is
not onboarding consent.

For HTTP development that does not need certificates, start an unprivileged
proxy deliberately. Choose an unused port above 1023; this example uses 1355:

```sh
PORTLESS_SYNC_HOSTS=0 PORTLESS_LAN=0 \
  ./node_modules/.bin/portless proxy start --no-tls --port 1355
```

Then run the project's documented development command, for example:

```sh
PORTLESS_SYNC_HOSTS=0 PORTLESS_LAN=0 PORTLESS_HTTPS=0 PORTLESS_PORT=1355 \
  bun run dev
./node_modules/.bin/portless list
```

The HTTP URL includes the proxy port: `http://<app>.localhost:1355`.
Use project scripts to declare application names and commands, rather than
copying routes into a machine-global file. Portless persists proxy choices and
can reuse them on a later auto-start. Coordinate a mode/version change with
other projects using the same proxy; starting another project does not create
an independent machine-global service.

Chrome, Firefox, and Edge resolve `.localhost` names without a hosts entry.
Safari may require an explicit hosts update. If that is needed, review and run
`./node_modules/.bin/portless hosts sync` after routes exist; undo with
`./node_modules/.bin/portless hosts clean`. These commands modify `/etc/hosts`
and may request administrator privileges. Keep auto-sync disabled for trials.
Custom suffixes and framework routing requirements belong in the project.

`--lan` controls discovery and naming. In the evaluated 0.13.1 source, the
[proxy listener](https://github.com/vercel-labs/portless/blob/551434f0e2a688c1c7eccfead411eb2cdd3109c9/packages/portless/src/cli.ts#L573)
does not specify a loopback bind address, so omitting `--lan` does not establish
loopback-only exposure. Follow the project's network policy; LAN discovery,
Tailscale sharing, and public tunnels require their own explicit setup.

## HTTPS and certificate trust

If the project needs HTTPS, first stop its running development commands and
coordinate with other projects using the proxy. From the project directory:

```sh
./node_modules/.bin/portless proxy stop
# Explicitly generate this Mac's certificates and trust the local CA:
./node_modules/.bin/portless trust
# Explicitly start HTTPS; port 443 can request sudo:
PORTLESS_SYNC_HOSTS=0 PORTLESS_LAN=0 \
  ./node_modules/.bin/portless proxy start --https --port 443
PORTLESS_SYNC_HOSTS=0 PORTLESS_LAN=0 PORTLESS_HTTPS=1 PORTLESS_PORT=443 \
  bun run dev
```

Confirm the expected `https://<app>.localhost` URL in the browser, its certificate
issuer, and the project's own development checks. Trust can prompt for OS
authorization. A non-root macOS trust operation uses the login keychain; an
elevated operation can use the System keychain. TLS startup may also create or
trust a CA and attempts a separate HTTP redirect listener on port 80. Use the
same state directory consistently if the project selects `PORTLESS_STATE_DIR`.
Changing to `--no-tls` does not revoke an already trusted CA.

Portless can accept local custom certificate/key paths with `--cert` and `--key`.
Keep those paths and material outside this repository. Project documentation
owns any explicit `NODE_EXTRA_CA_CERTS` configuration for clients launched
outside Portless; never disable certificate verification to make HTTPS work.

OS startup service installation is a separate choice. If deliberately selected,
review `./node_modules/.bin/portless service --help` first. `service install`
can generate/trust certificates and create a root-owned macOS launchd service.
Record its Node/binary paths, state directory, and options locally; reinstall
deliberately if a project dependency or mise path changes. `service status`
inspects it; `service uninstall` stops and removes it, but certificate retirement
still needs the procedure below. Dotfiles do not install this service.

## Disposable validation

Use an installed project binary, a fresh state directory, and an unused high
port for a trial. Keep the following exports inside a subshell, and clear any
inherited LAN IP or sharing choices:

```sh
(
  set -eu
  umask 077
  trial_dir=$(mktemp -d)
  export PORTLESS_STATE_DIR="$trial_dir/state" PORTLESS_PORT=1355
  export PORTLESS_HTTPS=0 PORTLESS_SYNC_HOSTS=0 PORTLESS_LAN=0
  export PORTLESS_TLD=localhost PORTLESS_WILDCARD=0
  export PORTLESS_TAILSCALE=0 PORTLESS_FUNNEL=0
  unset PORTLESS_LAN_IP PORTLESS
  printf 'Trial directory: %s\n' "$trial_dir"
  ./node_modules/.bin/portless --version
  ./node_modules/.bin/portless --help
  PORTLESS=0 ./node_modules/.bin/portless run node -e \
    'console.log("Portless bypass works")'
  # Optional HTTP trial: run in the foreground and stop with Ctrl-C.
  ./node_modules/.bin/portless proxy start --no-tls --port "$PORTLESS_PORT" --foreground
)
```

The version/help/bypass checks do not create proxy state. The optional proxy
creates only trial state. A second terminal can run a synthetic app using the
same explicit environment and state directory, inspect the project binary's
`list` output, stop the app, and then run its `proxy stop` with that same
environment. Verify that the trial proxy has stopped before deleting only the
printed trial directory. Do not run `portless clean` to remove a disposable
trial: its scope extends beyond `PORTLESS_STATE_DIR`.

The 0.13.1 package was verified against the existing project lockfile's integrity
and exercised with Node 24.21.0: help/version, bypass, an isolated HTTP proxy,
synthetic application routing, route removal on exit, and explicit proxy stop.
The trial generated no certificates or trust/service actions and left the hosts
file unchanged. Browser HTTPS trust and OS startup service installation remain
manual onboarding checks.

## Shutdown, untrust, and retirement

For ordinary shutdown, stop the project's development command and run the
installed project's `portless proxy stop` only when other projects no longer
need that shared proxy. To bypass it for a development run, use the project's
documented direct script or `PORTLESS=0 bun run dev` when its scripts honor that
setting. Restarting an application can restart the proxy.

For complete retirement, stop all dependent projects, inspect
`./node_modules/.bin/portless clean --help`, and deliberately run
`./node_modules/.bin/portless clean` while the binary is still installed.
In 0.13.1, this stops the proxy, uninstalls a startup service, removes CA trust,
removes known generated state from `~/.portless`, legacy `/tmp/portless`, and
the selected custom state directory, and cleans the Portless hosts block.
It may request sudo. On macOS its CA removal can delete multiple certificates
named `portless Local CA` from login and System keychains, so it is unsuitable
for retiring only one of several independent Portless setups. Custom certificate
files supplied with `--cert` and `--key` are retained.
See the versioned [cleanup scope](https://github.com/vercel-labs/portless/blob/551434f0e2a688c1c7eccfead411eb2cdd3109c9/packages/portless/src/clean-utils.ts)
and [macOS CA removal](https://github.com/vercel-labs/portless/blob/551434f0e2a688c1c7eccfead411eb2cdd3109c9/packages/portless/src/certs.ts#L971).

For selective untrust, identify the local CA by its SHA-256 fingerprint before
changing state:

```sh
openssl x509 -in /path/to/selected/state/ca.pem -noout -fingerprint -sha256
```

Use Keychain Access to remove trust and delete only the matching CA in the
keychain where it was installed. After manual removal, remove that state
directory's generated `ca.trusted` marker so Portless does not use stale cached
trust. Keep the public CA certificate until OS trust removal is verified; never
delete a directory first and assume its CA is untrusted. Check both login and
System keychains and the hosts block after retirement. If cleanup reports a
trust-removal error, resolve it explicitly in Keychain Access. A successful exit
alone is insufficient because cleanup can continue after an untrust warning.
Then remove the development dependency through the owning project's review.

`~/.portless` and custom state directories stay unmanaged. Never import their
routes, logs, PID/process state, persisted proxy markers, host certificates,
CA/server private keys, or generated CA/server certificates into dotfiles.
Do not copy the entire directory, including for fixtures or backups in Git.
Every Mac creates and trusts its own CA only during explicit HTTPS onboarding.
