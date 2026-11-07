# Portless development and macOS service

Projects own their Portless dependency, lockfile, routes, application commands,
and Compose configuration. Use the reviewed project binary for everyday work.
The machine's optional startup proxy has a different lifetime: it must not refer
to a project checkout or a versioned Homebrew Cellar directory.

Dotfiles owns the explicit acquisition and repair procedure for that service's
durable runtime. The exact package selection and registry integrity live in
[`tools/portless`](../tools/portless/package.json) and its Bun lockfile; it is
independent of project updates and ordinary `dotfiles install/update`. No
Portless software, launchd service, CA trust, or proxy is installed or started
by shell startup or chezmoi application. The installed package, private state,
certificates, logs and launchd plist stay machine-local and outside the manifest.
See the [selected upstream guide](https://github.com/vercel-labs/portless/blob/v0.16.0/README.md).

## Repair an existing startup service explicitly

Run from the reviewed dotfiles checkout as the owning user, never with sudo:

```sh
python3 scripts/portless-service.py install-runtime
python3 scripts/portless-service.py prepare --output /tmp/portless-service-review
```

`install-runtime` uses Bun's frozen lockfile and disables lifecycle scripts. It
installs the self-contained package at `~/.local/share/portless/<version>` with
`dist/cli.js` directly beneath it. It validates every published file against the reviewed SHA-256/size inventory
and compares the locked download before accepting an existing tree. Changed,
unowned, externally writable or linked content is refused without replacement.
The known nonexecutable Atelier repair marker is preserved only when its
repository, purpose, version, target and complete file inventory agree; other
extra files are refused. Download staging is removed on failure. Installation does not
start the proxy, trust certificates, change a service, or alter project dependencies.

`prepare` reads the existing `/Library/LaunchDaemons/sh.portless.proxy.plist`,
checks its label, foreground command and owning user's home, and stages a private
backup, replacement plist and hash receipt. It changes only the Node and Portless
entrypoint arguments. Existing proxy flags, state directory, log path, UID/GID,
CA and trust remain unchanged. Before executing the CLI, it validates every package file against the reviewed
integrity inventory. It then checks the package version and Mise's installed Node major alias against the reviewed global Node pin. Project
selectors and PATH cannot redirect that Node selection. A custom `MISE_DATA_DIR`
must describe the intended existing installation. The output directory must not
already exist. Staging does not apply or restart anything.

Review the staged plist locally; it contains machine paths and may contain
private environment overrides, so do not publish it. Check that only the first
two `ProgramArguments` changed and that the original file's SHA-256 still
matches `receipt.json` immediately before application. Preserve the backup
until the replacement has been verified. Administrator application is a separate
explicit operation, coordinated with other projects using the shared proxy:

```sh
plutil -lint /tmp/portless-service-review/candidate.plist
# After reviewing the paths, preserved settings, and unchanged original hash:
sudo launchctl bootout system/sh.portless.proxy
sudo install -o root -g wheel -m 644 /tmp/portless-service-review/candidate.plist \
  /Library/LaunchDaemons/sh.portless.proxy.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/sh.portless.proxy.plist
```

A missing running job can make `bootout` fail; establish that it is absent
before continuing. If bootstrap fails, retain its error and restore the reviewed
`original.plist` with the same `install` and `bootstrap` steps. Never run broad
`portless clean` as part of service repair: it can retire shared CA trust and routes.

Use `launchctl print system/sh.portless.proxy` to check process state, then
verify an existing project's named HTTPS URL and certificate issuer in a browser.
A loaded plist alone does not prove routing or trust. Check the selected runtime's
`service status` with the same Node, HOME and state directory. Keep diagnostics
local; do not copy logs, certificates, keys or plist receipts into Git.

Mise's major alias survives minor Node upgrades, unlike a Cellar version path.
Retiring that Node major, changing `MISE_DATA_DIR`, or upgrading the locked Portless
package requires explicit reinstallation, preparation, review and service restart.
A package upgrade must refresh and qualify its locked package and SHA/size inventory together.
There is no automatic major-version repair or automatic service upgrade. Keep
the prior runtime and Node installation until the new service is qualified.
A root launchdaemon executes user-owned runtime code, as Portless's own service
installer does; keep those files private to the owning user and trusted administrators.

This command repairs an existing macOS service only. For first installation,
review the selected runtime's `service install --help`, use that durable runtime
with the selected Mise Node, then run `prepare` to normalize the stable Node alias.
First installation can create/trust certificates and request administrator access.
`--unprivileged` changes proxy binding/elevation behavior; it does not convert
a root launchdaemon into a per-user service. A service migration needs its own review.

## Project installation

Read the project's package manager, runtime selectors and development instructions.
For a Bun-owned project, use `bun install --frozen-lockfile` and its installed
`./node_modules/.bin/portless`. Never silently supply another version through an
on-demand package download. Coordinate project/service version compatibility: the
shared state format is pre-1.0 and can change between releases.

## Localhost and normal development

Portless defaults to HTTPS on port 443, generates local certificates, and
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

`--lan` controls discovery and naming. Omitting `--lan` does not by itself establish loopback-only exposure.
Read the selected version's listener and `--unprivileged` behavior before choosing a network policy. Follow the project's network policy; LAN discovery,
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

## Disposable validation and retirement

`MISE_OFFLINE=1 ./scripts/check` exercises runtime installation with synthetic
packages, refusal of changed/symlink trees, failure cleanup, and preparation
against a disposable home and synthetic plist. It also checks the complete
chezmoi manifest and repeated application. These checks never start a proxy or
modify launchd, trust or the real home. A locked package acquisition and
help/version check can additionally run in a disposable home before activation.
Host routing, restart and browser trust remain explicit activation checks.

For ordinary shutdown, coordinate other projects before stopping the shared proxy.
For complete retirement, inspect the selected version's `service uninstall` and
`clean --help` first. Service removal and CA retirement are separate operations.
`clean` may remove shared routes, state and certificates from multiple locations
and keychains; it is unsuitable for deleting one trial. Identify the local CA's
SHA-256 fingerprint before selective trust removal and verify both login and
System keychains. Keep its public certificate until trust retirement is verified;
deleting a state directory alone does not revoke trust.

Generated `~/.portless`, custom state directories, installation trees and repair
backups stay unmanaged. Each machine explicitly generates and trusts its own CA.
