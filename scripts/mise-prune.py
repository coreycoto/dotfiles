#!/usr/bin/env python3
"""Preview or prune unused versions of explicitly named Mise tools."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="remove versions Mise considers unused")
    parser.add_argument("tools", nargs="+", help="Mise tool names to review")
    args = parser.parse_args()
    if any("@" in name or name.startswith("-") or "/../" in name for name in args.tools):
        parser.error("Name tools without versions or options")

    print("Mise only knows tracked configurations and tool stubs; review untracked projects,", flush=True)
    print("ad-hoc version use and rollback needs before applying. The result can change.", flush=True)
    command = ["mise", "--cd", str(Path.home())]
    if args.apply:
        command.append("--yes")
    command += ["prune", "--tools"]
    if not args.apply:
        command.append("--dry-run")
    command += args.tools
    print(shlex.join(command), flush=True)
    env = {**os.environ, "MISE_OFFLINE": "1", "MISE_AUTO_INSTALL": "false",
           "MISE_EXEC_AUTO_INSTALL": "false", "MISE_NOT_FOUND_AUTO_INSTALL": "false"}
    try:
        result = subprocess.run(command, cwd=Path.home(), env=env)
    except OSError as error:
        print(f"Mise prune could not start: {error}.", file=sys.stderr)
        return 1
    return result.returncode if result.returncode >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
