# ShellCheck: supported shell dialects

Use the script's shebang and repository configuration to select the intended
shell. For supported sh/bash/dash/ksh scripts:

```sh
shellcheck scripts/check scripts/enable-hooks
```

Choose `--shell=sh` or `--shell=bash` only when that dialect is intended and
cannot be inferred; forcing Bash on a Zsh script does not validate it. Read
repository `.shellcheckrc` and diagnostic directives before changing exclusions.
ShellCheck does not support Zsh. In these dotfiles, check Zsh syntax separately:

```sh
zsh -n home/dot_zshrc
zsh -n home/dot_config/zsh/environment.zsh
```

For multiple files, invoke `zsh -n` once per file; additional operands can be
script arguments rather than separately parsed files. Shell syntax validation
and static diagnostics do not exercise PATH precedence, hooks, or repeated
sourcing; use the repository's disposable-shell tests for those behaviors.

Fix quoting, splitting, or portability at the source. When a diagnostic is an
intentional exception, use a narrow suppression with a reason rather than a
project-wide disable. Static linting does not execute the script; sourcing an
unfamiliar script to test it can have side effects.

Source: [supported shells](https://www.shellcheck.net/wiki/SC1071).
