#!/usr/bin/env python3
"""Install Mise tools or upgrade the selected Mise and Homebrew tools."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tomllib


REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    source = REPO / "home/dot_config/mise/config.toml"
    tools = tomllib.loads(source.read_text())["tools"]
    command = ["mise", "--cd", str(Path.home())]
    command += ["upgrade", "--global"] if args.update else ["install"]
    if args.update and not args.apply:
        command += ["--dry-run"]
    command += list(tools)
    if args.apply or args.update:
        config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "mise/config.toml"
        if not config.is_file() or config.read_bytes() != source.read_bytes():
            parser.error("Apply the reviewed ~/.config/mise/config.toml before installing or previewing upgrades")
    if args.update:
        missing = [name for name in ("mise", "brew") if shutil.which(name) is None]
        if missing:
            parser.error("Required update command not found: " + ", ".join(missing))
    print(shlex.join(command), flush=True)
    if not (args.apply or args.update):
        return 0

    mode = ("upgrade" if args.apply else "upgrade preview") if args.update else "installation"
    try:
        result = subprocess.run(command, cwd=Path.home(), env={**os.environ, "MISE_UPGRADE_AUTO_PRUNE": "false"})
    except OSError as error:
        suffix = " Homebrew was not run." if args.update else ""
        print(f"Mise {mode} could not start: {error}.{suffix}", file=sys.stderr)
        return 1
    if result.returncode:
        if args.update:
            print(f"Mise {mode} failed (exit {result.returncode}); it may have partially completed. Homebrew was not run.", file=sys.stderr)
        return result.returncode if result.returncode > 0 else 1
    if not args.update:
        return 0
    brew_command = ["brew", "upgrade"]
    if not args.apply:
        brew_command.append("--dry-run")
    print(shlex.join(brew_command), flush=True)
    try:
        result = subprocess.run(brew_command, cwd=Path.home(), env={**os.environ, "HOMEBREW_NO_INSTALL_CLEANUP": "1"})
    except OSError as error:
        print(f"Mise {mode} completed; Homebrew {mode} could not start: {error}.", file=sys.stderr)
        return 1
    if result.returncode:
        print(f"Mise {mode} completed; Homebrew {mode} failed (exit {result.returncode}) and may have partially completed.", file=sys.stderr)
        return result.returncode if result.returncode > 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
