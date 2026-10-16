# Rust toolchains and local configuration

Mise owns the selected Rust toolchains through its Rustup backend. The authored
default is Rust `1.97.1`, the minimal installation profile, and the additional
`rustfmt` and `clippy` components. Its isolated homes are
`~/.local/share/dotfiles/rustup` and `~/.local/share/dotfiles/cargo`, selected by
the `MISE_RUSTUP_HOME` and `MISE_CARGO_HOME` settings already in this repository.
Installed toolchains, Cargo binaries, registry data, and credentials stay local.

## Fresh-machine setup and selection

After the reviewed dotfiles are explicitly applied, install the declared runtime
and regenerate shims as described in [tool ownership](tool-ownership.md):

```sh
mise install rust@1.97.1
mise reshim
mise exec -- rustc --version
mise exec -- cargo --version
mise exec -- rustup show active-toolchain
mise exec -- rustup component list --installed
mise exec -- sh -c 'printf "%s\n" "$RUSTUP_HOME" "$CARGO_HOME" "$RUSTUP_TOOLCHAIN"'
```

Verify the isolated homes, exact version, and required components before using
the toolchain. Installation is explicit; startup and command resolution do not
install missing tools. The Rustup global profile setting is separate from mise's
per-install profile; inspect actual components instead of assuming that changing
a profile removes existing components.

Mise passes Rust home selection and `RUSTUP_TOOLCHAIN` to the command it runs.
Standalone Rustup, direct toolchain binaries, and editors can use other homes
or selection rules. Prefer the mise shim or `mise exec` and check the effective
environment in the actual project. Explicit Cargo/Rustup home overrides can
change ownership. See [mise Rust](https://mise.jdx.dev/lang/rust.html).

Review `rust-toolchain.toml`, `rust-toolchain`, `mise.toml`, local selectors,
Cargo's `rust-version`, and CI requirements before choosing a project toolchain.
Rustup's environment override can take precedence over a toolchain file. If a
project relies on those files, explicitly enable and verify mise's Rust
idiomatic-file discovery for that project, or select the matching version
through its reviewed mise configuration. Keep its required components and
targets, and retain independent MSRV checks. A current developer version does
not prove minimum-version compatibility. See [Rustup overrides](https://rust-lang.github.io/rustup/overrides.html).

For each maintained workspace, run its documented build, format, lint, and test
checks through the selected toolchain. Start with locked/offline checks when
the dependency cache is available; a missing cached dependency is an explicit
prerequisite, not permission to download or relax the lockfile. For example:

```sh
mise exec -- cargo fmt --all -- --check
mise exec -- cargo check --all-targets --all-features --locked --offline
mise exec -- cargo clippy --all-targets --all-features --locked --offline -- -D warnings
mise exec -- cargo test --all-targets --all-features --locked --offline
```

Apply the owning project's scope/options rather than assuming every workspace
supports all features together. Review local/global Cargo configuration when
selecting a toolchain, including registries, aliases, linkers, targets, and
build wrappers. See [Cargo configuration](https://doc.rust-lang.org/cargo/reference/config.html).

## Existing tools and local configuration

Before changing an existing installation, inspect its installed toolchains,
components, targets, directory overrides, Cargo `bin`, `.crates.toml` and
`.crates2.json`, and authored `config`/`config.toml`/`env` settings. Review
credentials and custom registry configuration privately; do not print or import
them. Reinstall any unique CLI through its chosen owner at a reviewed version,
then verify its command path and real workflow. Do not copy installed binaries
or treat a generated proxy as a separately installed CLI.

Cargo-installed application tools need their own installation/version selection.
An explicit Cargo installation uses the effective `CARGO_HOME`; mise shims do
not imply that every newly installed Cargo CLI is discoverable. Verify its
executable path and deliberately choose any necessary local PATH addition.
Prefer an already selected package owner when that avoids duplicate maintenance.
Merge useful authored preferences into the selected local configuration only
after review, preserving unrelated entries and keeping credentials private.

## Recovery

Restore the selected local runtime, PATH and home overrides from their private
backup, then verify the affected project through the intended toolchain.
Preserve other installations while diagnosing. A working current toolchain does
not prove MSRV compatibility or that an older installation is unused.
See [recovery](recovery.md) for configuration and package boundaries.
