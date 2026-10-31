#!/usr/bin/env python3
"""Maintain tools and validate the dotfiles checkout."""

import argparse
import os
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(prog="dotfiles", description=__doc__)
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    install = commands.add_parser("install", help="install the selected Mise tools")
    install.add_argument("--dry-run", action="store_true", help="print the install command without running it")
    update = commands.add_parser("update", help="upgrade Homebrew packages and selected Mise tools")
    update.add_argument("--dry-run", action="store_true", help="preview available upgrades")
    commands.add_parser("status", help="check Homebrew and Mise versions and available updates")
    commands.add_parser("check", help="run the checkout's validation suite in a disposable home")
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return
    if args.command == "check":
        script = REPO / "scripts/check"
        os.chdir(REPO)
        os.execv(str(script), [str(script)])
    if args.command == "status":
        zsh = "/bin/zsh"
        project_bins = REPO / "home/dot_config/zsh/project-bins.zsh"
        diagnostics = REPO / "home/dot_config/zsh/diagnostics.zsh"
        command = 'source "$1" && source "$2" && builtin cd -- "$HOME" && _dotfiles_status'
        os.execv(zsh, [zsh, "-dfc", command, "dotfiles-status", str(project_bins), str(diagnostics)])

    # The launcher disables Mise changes while starting Python, then hands
    # the caller's original environment back to the actual upgrade commands.
    if args.command == "update" and os.environ.pop("DOTFILES_UPDATE_BOOTSTRAP", "") == "1":
        for name in ("MISE_OFFLINE", "MISE_AUTO_INSTALL", "MISE_EXEC_AUTO_INSTALL", "MISE_NOT_FOUND_AUTO_INSTALL"):
            present = os.environ.pop("DOTFILES_SAVED_PRESENT_" + name)
            saved = os.environ.pop("DOTFILES_SAVED_" + name, "")
            if present == "1":
                os.environ[name] = saved
            else:
                os.environ.pop(name, None)

    script = REPO / "scripts/mise-tools.py"
    flags = ["--update"] if args.command == "update" else []
    if not args.dry_run:
        flags.append("--apply")
    os.execv(sys.executable, [sys.executable, str(script), *flags])


if __name__ == "__main__":
    main()
