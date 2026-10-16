# mise: runtime selection

Inspect selection from the project directory:

```sh
mise ls
mise which python
mise which node
mise exec -- rustc --version
```

Run only commands relevant to that project. Read `mise.toml`, local overlays,
`.python-version`, Rust toolchain files, package runtime declarations, and CI.
Language-specific version files may require mise's idiomatic-file discovery to
be enabled; their presence does not prove mise selected them. `mise which`
shows resolution, while `command -v` may show only a shim.

For an explicitly authorized setup, install the declared version with
`mise install TOOL@VERSION`, then run `mise reshim` when command shims need
refreshing. `mise exec -- COMMAND` supplies the selected runtime without shell
activation; it can also load configured project environment and wrappers.
Inspect unfamiliar project configuration before executing its tasks.

`mise use` writes version configuration; it is not an inspection command.
Keep project pins, minimum-supported versions, and personal defaults distinct.
These dotfiles disable automatic installation and missing-version fallback.

Mise's Rust backend uses rustup. The dotfiles isolate its Cargo/Rustup state
through `MISE_CARGO_HOME` and `MISE_RUSTUP_HOME`; standalone rustup commands can
select different state. Use `mise exec -- rustup show active-toolchain` when
comparing selection. Do not add Homebrew Rust/LLVM to fix a missing mise pin.

Mise owns Bun as well as Node, Python and Rust. Node, Python and Rust defaults
remain exact; global Bun follows `1` (Bun 1.x) with update checks every 6 hours.
Replaced Mise versions and native Homebrew packages remain recovery options.
Duplicate Homebrew CLIs may have been retired; inspect the installed inventory
before relying on an old executable path for rollback.
Global CLI entries can opt into
`auto_update = "6h"`; exact project versions remain fixed. `dotfiles-tools`
previews installation and `--update` previews upgrades; `--apply` performs them.
Use `MISE_OFFLINE=1` for status checks or shell initialization that invokes a
shim, so those reads never trigger upgrades.

Sources: [dev tools](https://mise.jdx.dev/dev-tools/),
[configuration](https://mise.jdx.dev/configuration.html),
[shims](https://mise.jdx.dev/dev-tools/shims.html).
