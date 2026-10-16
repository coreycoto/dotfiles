#!/usr/bin/env python3
"""Preview Mise tool installation; --update previews upgrades, --apply performs them."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
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
    print(shlex.join(command), flush=True)
    if args.apply or args.update:
        config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "mise/config.toml"
        if not config.is_file() or config.read_bytes() != source.read_bytes():
            parser.error("Apply the reviewed ~/.config/mise/config.toml before installing or previewing upgrades")
        subprocess.run(command, check=True, env={**os.environ, "MISE_UPGRADE_AUTO_PRUNE": "false"})


if __name__ == "__main__":
    main()
