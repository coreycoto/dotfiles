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
    update = commands.add_parser("update", help="upgrade the selected Mise tools within their existing requests")
    update.add_argument("--dry-run", action="store_true", help="preview available upgrades")
    commands.add_parser("check", help="run the checkout's validation suite in a disposable home")
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return
    if args.command == "check":
        script = REPO / "scripts/check"
        os.chdir(REPO)
        os.execv(str(script), [str(script)])

    script = REPO / "scripts/mise-tools.py"
    flags = ["--update"] if args.command == "update" else []
    if not args.dry_run:
        flags.append("--apply")
    os.execv(sys.executable, [sys.executable, str(script), *flags])


if __name__ == "__main__":
    main()
